from nonebot import on_message
from nonebot.adapters.onebot.v11 import Bot, MessageEvent
import httpx
import xml.etree.ElementTree as ET
from nonebot.exception import FinishedException

# 推荐板块示例
RECOMMENDED_CATEGORIES = {
    "cs.AI": "人工智能 (Artificial Intelligence)",
    "cs.CL": "计算语言学 (Computation and Language)",
    "cs.CV": "计算机视觉 (Computer Vision)",
    "cs.LG": "机器学习 (Machine Learning)",
    "stat.ML": "统计机器学习 (Statistical Machine Learning)",
    "cs.RO": "机器人 (Robotics)",
    "cs.CR": "密码学与安全 (Cryptography and Security)",
    "cs.NI": "网络与互联网架构 (Networking and Internet Architecture)"
}

# 自定义触发器
def arxiv_starts_rule(event: MessageEvent) -> bool:
    """识别以 .arxiv 开头"""
    text = event.get_plaintext().strip().lower()
    return text.startswith(".arxiv")

# 消息监听
arxiv_handler = on_message(rule=arxiv_starts_rule, priority=1, block=True)

@arxiv_handler.handle()
async def handle_arxiv(bot: Bot, event: MessageEvent):
    args = event.get_plaintext().strip().split()
    if args[0].lower() == ".arxiv":
        args = args[1:]  # 去掉.arxiv

    # -------- list 列出推荐分类 --------
    if len(args) == 1 and args[0].lower() == "list":
        categories = "\n".join([f"{key}: {value}" for key, value in RECOMMENDED_CATEGORIES.items()])
        await arxiv_handler.finish(f"📚 推荐板块如下（访问：https://arxiv.org/category_taxonomy 查看全部板块目录）:\n{categories}")

    # -------- 参数校验 --------
    if not args:
        await arxiv_handler.finish("❗ 用法: arxiv [分类] [数量, 默认为5]，如 arxiv cs.AI 5")

    category = args[0]  # ⚠️ 不检查合法性，允许一切分类尝试
    max_results = int(args[1]) if len(args) > 1 and args[1].isdigit() else 5

    query_url = f"http://export.arxiv.org/api/query?search_query=cat:{category}&start=0&max_results={max_results}"

    # -------- 查询 --------
    try:
        async with httpx.AsyncClient(timeout=10) as client:
            response = await client.get(query_url)
            response.raise_for_status()
    except httpx.HTTPError as e:
        await arxiv_handler.finish(f"❌ 查询失败（网络或请求异常）：{e}")

    # -------- 解析 --------
    try:
        root = ET.fromstring(response.content)
        ns = {'atom': 'http://www.w3.org/2005/Atom'}
        entries = root.findall('atom:entry', ns)

        if not entries:
            await arxiv_handler.finish("⚠️ 没找到相关论文，可能分类代码错误。请访问：https://arxiv.org/category_taxonomy 查看板块目录")

        result = ["📑 最新论文："]
        for entry in entries:
            title = entry.find('atom:title', ns).text.strip().replace('\n', ' ')
            link = entry.find('atom:id', ns).text.strip()
            result.append(f"- {title}\n🔗 {link}")

        await arxiv_handler.finish("\n\n".join(result))

    except FinishedException:
        raise
    except Exception as e:
        await arxiv_handler.finish(f"❌ 数据解析失败：{e}")
