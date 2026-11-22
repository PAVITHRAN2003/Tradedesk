"""Your supervisor + 4 agents, refactored into an importable async function."""
from datetime import datetime
from zoneinfo import ZoneInfo

from langchain.chat_models import init_chat_model
from langchain_core.messages import AIMessage
from langchain_mcp_adapters.client import MultiServerMCPClient
from langgraph.prebuilt import create_react_agent
from langgraph_supervisor import create_supervisor

from ..config import settings
from .market_tools import get_market_data

AGENT_NAMES = {"stock_finder_agent", "market_data_agent", "news_analyst_agent", "price_recommender_agent"}

STOCK_FINDER = """You are a stock research analyst specializing in the Indian Stock Market (NSE). Select 2 promising, actively traded NSE-listed stocks for short term trading, using web search.
Use search_engine (at most 2 searches) to find NSE stocks that are currently in the news with strong volume or momentum (top gainers, volume spikes, results, upgrades). If the market is closed, use the latest session's movers.
Avoid penny stocks and illiquid companies. State only facts that appear in your search results and name the source site for each. If a figure is not in the results, leave it out; never invent numbers.
Output: stock names, NSE tickers and brief reasoning for each. Plain structured text."""

MARKET_DATA = """You are a market data analyst for NSE stocks. You are given tickers (eg RELIANCE, INFY).
Call get_market_data ONCE with all the tickers. Then report, per stock, exactly what the tool returned: as_of date, last and previous close, 1/5/21-day change %, volume vs 20-day average, RSI14, 50 and 200-day moving averages, 52-week range, volatility spike flag.
Use INR. Do NOT invent or estimate any number. If the tool returns an error for a ticker, say so."""

MARKET_DATA_WEB = """You are a market data analyst for NSE stocks. You are given tickers (eg RELIANCE, INFY).
Use search_engine and scrape_as_markdown to find, per stock: current price, previous close, today's volume, 7-day and 30-day trend, RSI and 50/200-day moving averages if shown.
Report only figures you actually found, with the source site and date. Write "not found" for anything missing. Do NOT estimate or invent numbers. Use INR."""


NEWS = """You are a financial news analyst. Given the names or the tickers of Indian NSE listed stocks, your job is to-
- Search for the most recent news articles (past 3-5 days)
- Summarize key updates, announcements, and events for each stock
- Classify each piece of news as positive, negative or neutral
- Highlight how the news might affect short term stock price

Present your response in a clear, structured format - one section per stock.
Use bullet points where necessary. Keep it short, factual and analysis-oriented"""

RECOMMENDER = """You are a trading strategy advisor for the Indian Stock Market. You are given market data (with an as_of date) and news summaries for each stock.
For each stock:
1. Recommend Buy, Sell, Hold or Avoid.
2. Give an entry price and an exit/target price in INR, anchored to the data given (last close, moving averages, 52-week range).
3. One or two sentences of reasoning that cite the given numbers.
Use ONLY the data you were given. If data is missing, say "not enough data" rather than guessing. Mention the as_of date. Keep it concise."""

SUPERVISOR = (
    "You are a supervisor managing four agents:\n"
    "- stock_finder_agent: searches the web for 2 promising NSE stocks\n"
    "- market_data_agent: fetches price/indicator data for given tickers\n"
    "- news_analyst_agent: summarizes recent news for given tickers\n"
    "- price_recommender_agent: gives Buy/Sell/Hold with entry and target prices\n"
    "You MUST call all four agents, in this order, one at a time (never in parallel, never skip one). "
    "Always pass the chosen tickers and the previous agent's findings in your instruction to the next agent. "
    "Do not do any work yourself and do not ask the user to confirm anything.\n"
    "When all four are done, write a short final summary: for each stock the action, entry, target and a "
    "one-line reason, plus the data as_of date. Use only what the agents reported. End with 'Not investment advice.'"
)


def _text(content) -> str:
    if isinstance(content, str):
        return content
    if isinstance(content, list):
        return "".join(c.get("text", "") if isinstance(c, dict) else str(c) for c in content)
    return str(content)


def _clip(x, limit):
    """Truncate tool output so one scraped page can't blow Groq's per-minute token limit."""
    if isinstance(x, str):
        return x if len(x) <= limit else x[:limit] + "\n…[truncated]"
    if isinstance(x, list):
        return [_clip(i, limit) if isinstance(i, str)
                else {**i, "text": _clip(i["text"], limit)} if isinstance(i, dict) and isinstance(i.get("text"), str)
                else i for i in x]
    return x


def _prepare_tools(tools):
    wanted = {n.strip() for n in settings.bright_data_tools.split(",") if n.strip()}
    picked = [t for t in tools if t.name in wanted] or tools  # fall back to all if names don't match
    limit = settings.tool_output_max_chars
    for t in picked:
        orig = t.coroutine
        if orig is None:
            continue
        as_pair = getattr(t, "response_format", "content") == "content_and_artifact"

        async def wrapped(*a, __orig=orig, __name=t.name, __pair=as_pair, **kw):
            if __name == "search_engine":
                kw["engine"] = "google"  # bing is flaky and rejects month filters
                if kw.get("time_range") not in ("day", "week"):
                    kw.pop("time_range", None)
            try:
                res = await __orig(*a, **kw)
            except Exception as e:  # hand the error to the model so it can retry, instead of killing the run
                msg = f"Tool error: {str(e)[:300]}. Retry once with a simpler query or different arguments."
                return (msg, None) if __pair else msg
            return (_clip(res[0], limit), *res[1:]) if isinstance(res, tuple) else _clip(res, limit)

        t.coroutine = wrapped
    return picked


def _make_model():
    extra = {}
    if "gpt-oss" in settings.groq_model:
        extra["reasoning_effort"] = "low"  # fewer hidden reasoning tokens per call
    return init_chat_model(f"groq:{settings.groq_model}", api_key=settings.groq_api_key,
                           temperature=0, max_retries=5, max_tokens=settings.groq_max_tokens, **extra)

async def run_stock_agent(query: str) -> dict:
    client = MultiServerMCPClient({
        "bright_data": {
            "command": "npx", "args": ["@brightdata/mcp"], "transport": "stdio",
            "env": {"API_TOKEN": settings.bright_data_api_token,
                    "WEB_UNLOCKER_ZONE": settings.web_unlocker_zone,
                    "BROWSER_ZONE": settings.browser_zone},
        }
    })
    web_tools = _prepare_tools(await client.get_tools())
    model = _make_model()

    now = datetime.now(ZoneInfo("Asia/Kolkata"))
    is_open = now.weekday() < 5 and (9, 15) <= (now.hour, now.minute) <= (15, 30)
    note = (f"\n\nIt is now {now.strftime('%A %d %B %Y, %H:%M')} IST. The NSE is currently "
            f"{'OPEN' if is_open else 'CLOSED'} (Mon-Fri 09:15-15:30 IST; exchange holidays are not tracked). "
            + ("" if is_open else "Because it is closed, treat all prices as the last session's close and phrase "
               "advice for the next trading session. ")
            + "Never assume a year or a price from memory; use only data your tools return. "
              "Make at most 2 tool calls, then reply with concise findings under 250 words.")
    web_note = (" Tool notes: call search_engine with a short query and no date-range arguments; "
                "use scrape_as_markdown only on a specific URL.")

    def agent(prompt, name, tools):
        return create_react_agent(model, tools, prompt=prompt, name=name)

    if settings.market_data_source == "web":
        market_agent = agent(MARKET_DATA_WEB + note + web_note, "market_data_agent", web_tools)
    else:
        market_agent = agent(MARKET_DATA + note, "market_data_agent", [get_market_data])

    graph = create_supervisor(
        model=_make_model(),
        agents=[
            agent(STOCK_FINDER + note + web_note, "stock_finder_agent", web_tools),
            market_agent,
            agent(NEWS + note + web_note, "news_analyst_agent", web_tools),
            agent(RECOMMENDER + note, "price_recommender_agent", []),
        ],
        prompt=SUPERVISOR + note,
        add_handoff_back_messages=True,
        output_mode="last_message",
    ).compile()

    # MCP tools are async-only, so use ainvoke (the sync .stream() in the original can't run them)
    result = await graph.ainvoke({"messages": [{"role": "user", "content": query}]},
                                 {"recursion_limit": 60})

    steps = []
    for m in result["messages"]:
        if (isinstance(m, AIMessage) and m.name in AGENT_NAMES and not m.tool_calls):
            text = _text(m.content).strip()
            if text and not text.startswith("Transferring back"):
                steps.append({"agent": m.name, "content": text})
    final = _text(result["messages"][-1].content).strip()
    return {"final": final, "steps": steps}