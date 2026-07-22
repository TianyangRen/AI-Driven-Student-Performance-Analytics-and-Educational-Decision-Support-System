"""pytest 夹具：浏览器驱动 + 服务连通性检查。

约定（见 README）：后端跑在 :8001、前端跑在 :5173，测试只连不起。
可用环境变量覆盖：
    E2E_BASE_URL   前端地址（默认 http://localhost:5173）
    E2E_HEADLESS   0 = 有头模式（实时观看），其它 = 无头（默认）
"""
import os
import shutil
import urllib.request

import pytest
from selenium import webdriver
from selenium.webdriver.chrome.options import Options

BASE_URL = os.environ.get("E2E_BASE_URL", "http://localhost:5173").rstrip("/")
HEADLESS = os.environ.get("E2E_HEADLESS", "1") != "0"


def _drop_stale_chromedriver_from_path():
    """若 PATH 里的 chromedriver 与本机 Chrome 大版本不符，Selenium Manager 会
    误用它而报 SessionNotCreated。把它所在目录从（本进程的）PATH 移除，Selenium
    Manager 便会自动下载匹配版本到自己的缓存。只影响测试进程，不动系统。"""
    for _ in range(10):  # 循环处理多个 PATH 目录都有 chromedriver 的情况
        found = shutil.which("chromedriver")
        if not found:
            return
        bad_dir = os.path.dirname(found)
        os.environ["PATH"] = os.pathsep.join(
            p for p in os.environ.get("PATH", "").split(os.pathsep) if p != bad_dir)


_drop_stale_chromedriver_from_path()


@pytest.fixture(scope="session")
def base_url():
    return BASE_URL


@pytest.fixture(scope="session", autouse=True)
def _ensure_servers():
    """开跑前先探活前端与后端，缺一个就用清晰提示直接终止，省得一堆超时。"""
    try:
        urllib.request.urlopen(BASE_URL, timeout=5)
    except Exception as exc:  # noqa: BLE001
        pytest.exit(
            f"前端无法访问 {BASE_URL}（{exc}）。请先启动：\n"
            f"  cd web-platform/frontend && npm run dev",
            returncode=1,
        )
    try:
        # /api 由 vite 代理到后端 :8001；health 无需鉴权
        urllib.request.urlopen(f"{BASE_URL}/api/v1/health", timeout=10)
    except Exception as exc:  # noqa: BLE001
        pytest.exit(
            f"后端无法访问 {BASE_URL}/api/v1/health（{exc}）。请先启动：\n"
            f"  cd web-platform/backend && uv run python manage.py runserver 8001",
            returncode=1,
        )


@pytest.fixture()
def driver():
    options = Options()
    if HEADLESS:
        options.add_argument("--headless=new")
    options.add_argument("--window-size=1440,1000")
    options.add_argument("--no-sandbox")
    options.add_argument("--disable-gpu")
    options.add_argument("--disable-dev-shm-usage")
    drv = webdriver.Chrome(options=options)
    drv.set_page_load_timeout(30)
    try:
        yield drv
    finally:
        drv.quit()
