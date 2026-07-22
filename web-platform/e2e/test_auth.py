"""登录 / 注册 端到端流程。"""
from selenium.webdriver.common.by import By
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.support.ui import WebDriverWait

from helpers import login, register, unique, wait_url_contains


def test_register_new_user_lands_on_dashboard(driver, base_url):
    register(driver, base_url, username=f"e2e_{unique()}", password="pw123456")
    assert "/dashboard" in driver.current_url


def test_register_as_admin_is_downgraded(driver, base_url):
    """注册时即便选了 ADMIN，后端也强制降级为 INSTRUCTOR（提权回归，对应 #1）。"""
    register(driver, base_url, username=f"e2e_admin_{unique()}",
             password="pw123456", role="ADMIN")
    driver.get(base_url + "/profile")
    # Profile 用硬编码英文 Tag 显示角色
    WebDriverWait(driver, 15).until(
        EC.presence_of_element_located((By.CSS_SELECTOR, ".ant-tag")))
    tags = [t.text for t in driver.find_elements(By.CSS_SELECTOR, ".ant-tag")]
    assert any("Instructor" in t for t in tags), f"角色标签应为 Instructor，实际：{tags}"
    assert not any("Administrator" in t for t in tags), f"不应出现 Administrator：{tags}"


def test_login_valid_reaches_dashboard(driver, base_url):
    username = f"e2e_{unique()}"
    register(driver, base_url, username=username, password="pw123456")  # 自动登录
    login(driver, base_url, username, "pw123456")                       # 登出后再登录
    wait_url_contains(driver, "/dashboard")
    assert "/dashboard" in driver.current_url


def test_login_invalid_shows_error(driver, base_url):
    login(driver, base_url, username=f"nouser_{unique()}", password="wrongpass")
    # 错误凭据：弹出错误提示且停留在 /login，不进 dashboard
    WebDriverWait(driver, 15).until(
        EC.visibility_of_element_located((By.CSS_SELECTOR, ".ant-message-error")))
    assert "/login" in driver.current_url
    assert "/dashboard" not in driver.current_url
