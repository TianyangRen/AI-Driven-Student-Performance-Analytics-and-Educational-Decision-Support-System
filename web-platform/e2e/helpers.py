"""页面动作辅助函数。

抗 i18n 策略（应用已切法语，文案会变）：
  · 表单输入用 antd 生成的稳定 id（#username / #code / #section_code …）
  · 登录/注册提交用 form 内的 button[type=submit]（不依赖按钮文案）
  · role / course 这类 antd Select 用「按范围点开 + 按文本或位置选项」
  · Courses / Sections 两页的按钮文案是硬编码英文，可按文本取
"""
import time

from selenium.webdriver.common.by import By
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.support.ui import WebDriverWait

TIMEOUT = 15


def unique():
    """毫秒时间戳尾 9 位——给用户名/课程码加后缀，避免 unique 约束冲突、可反复跑。"""
    return str(int(time.time() * 1000))[-9:]


def _wait(driver, timeout=TIMEOUT):
    return WebDriverWait(driver, timeout)


def wait_url_contains(driver, part, timeout=TIMEOUT):
    _wait(driver, timeout).until(EC.url_contains(part))


def fill(driver, css, value):
    el = _wait(driver).until(EC.element_to_be_clickable((By.CSS_SELECTOR, css)))
    el.clear()
    el.send_keys(value)
    return el


def _submit_form(driver):
    """点登录/注册表单里的提交按钮（唯一 button[type=submit]）。"""
    btn = _wait(driver).until(
        EC.element_to_be_clickable((By.CSS_SELECTOR, "form button[type='submit']")))
    btn.click()


def _clear_storage(driver):
    driver.execute_script("window.localStorage.clear();")


# --------------------------------------------------------------------- #
# antd Select：点开 + 选项
# --------------------------------------------------------------------- #
def pick_select(driver, scope_css=None, match_text=None, index=None):
    """点开一个 antd Select 并选中选项。

    scope_css  限定 Select 所在容器（如 '.ant-modal'）；None = 全页第一个 Select
    match_text 选包含该文本的选项（优先）
    index      按位置选（match_text 为空时用）
    """
    selector = ".ant-select-selector"
    if scope_css:
        selector = f"{scope_css} {selector}"
    control = _wait(driver).until(
        EC.element_to_be_clickable((By.CSS_SELECTOR, selector)))
    driver.execute_script("arguments[0].scrollIntoView({block:'center'});", control)
    control.click()

    open_opts = (".ant-select-dropdown:not(.ant-select-dropdown-hidden) "
                 ".ant-select-item-option")
    _wait(driver).until(EC.visibility_of_element_located((By.CSS_SELECTOR, open_opts)))
    options = driver.find_elements(By.CSS_SELECTOR, open_opts)

    if match_text is not None:
        for opt in options:
            if match_text in opt.text:
                opt.click()
                return
        raise AssertionError(
            f"未找到含 {match_text!r} 的选项；现有：{[o.text for o in options]}")
    options[index].click()


# --------------------------------------------------------------------- #
# 认证流程
# --------------------------------------------------------------------- #
def register(driver, base_url, username, password="pw123456",
             role=None, full_name=None, email=None):
    """走注册页；成功后应用自动登录并跳转 /dashboard。role='ADMIN' 时主动选管理员。"""
    driver.get(base_url + "/register")
    fill(driver, "#username", username)
    if full_name:
        fill(driver, "#full_name", full_name)
    if email:
        fill(driver, "#email", email)
    if role:
        # 选项顺序：[INSTRUCTOR, ADMIN]
        pick_select(driver, index=1 if role == "ADMIN" else 0)
    fill(driver, "#password", password)
    _submit_form(driver)
    wait_url_contains(driver, "/dashboard")


def login(driver, base_url, username, password):
    """先清 localStorage（等价登出）再走登录页，提交后不做断言（交给用例）。"""
    driver.get(base_url + "/login")
    _clear_storage(driver)
    driver.get(base_url + "/login")  # 重载让 AuthContext 读到已清空的存储
    fill(driver, "#username", username)
    fill(driver, "#password", password)
    _submit_form(driver)


# --------------------------------------------------------------------- #
# Courses / Sections 页动作
# --------------------------------------------------------------------- #
def click_button_with_text(driver, text):
    btn = _wait(driver).until(EC.element_to_be_clickable(
        (By.XPATH, f"//button[contains(normalize-space(.), '{text}')]")))
    btn.click()


def click_modal_create(driver):
    """点弹窗底部的 Create（okText 硬编码英文）。"""
    btn = _wait(driver).until(EC.element_to_be_clickable((
        By.XPATH,
        "//div[contains(@class,'ant-modal-footer')]"
        "//button[contains(normalize-space(.), 'Create')]")))
    btn.click()


def wait_table_contains(driver, text, timeout=TIMEOUT):
    _wait(driver, timeout).until(
        lambda d: text in d.find_element(By.CSS_SELECTOR, ".ant-table-tbody").text)
