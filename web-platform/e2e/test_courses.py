"""课程 / 教学班录入 端到端流程（含我们新增的校验在浏览器里生效）。"""
from selenium.webdriver.common.by import By
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.support.ui import WebDriverWait

from helpers import (
    click_button_with_text,
    click_modal_create,
    fill,
    pick_select,
    register,
    unique,
    wait_table_contains,
)


def _fresh_login(driver, base_url):
    """每个用例用一个全新教师账号，保证数据隔离与权限范围干净。"""
    register(driver, base_url, username=f"e2e_{unique()}", password="pw123456")


def test_create_course_uppercases_code(driver, base_url):
    """输入小写课程码，落库后应被规范化为大写（#3）。"""
    _fresh_login(driver, base_url)
    driver.get(base_url + "/courses")
    click_button_with_text(driver, "New course")

    code = f"e2e{unique()}"  # 全小写
    fill(driver, "#code", code)
    fill(driver, "#name", "E2E Course")
    fill(driver, "#term", "S26")
    click_modal_create(driver)

    wait_table_contains(driver, code.upper())
    body = driver.find_element(By.CSS_SELECTOR, ".ant-table-tbody").text
    assert code.upper() in body


def test_create_course_requires_fields(driver, base_url):
    """空表单提交应触发前端必填校验、不落行。"""
    _fresh_login(driver, base_url)
    driver.get(base_url + "/courses")
    click_button_with_text(driver, "New course")
    click_modal_create(driver)  # 什么都不填直接提交

    WebDriverWait(driver, 10).until(EC.visibility_of_element_located(
        (By.CSS_SELECTOR, ".ant-form-item-explain-error")))
    errors = driver.find_elements(By.CSS_SELECTOR, ".ant-form-item-explain-error")
    assert len(errors) >= 1
    # 弹窗仍在（未创建成功关闭）
    assert driver.find_elements(By.CSS_SELECTOR, ".ant-modal")


def test_create_section_uppercases_code(driver, base_url):
    """先建课程，再在其下建 section，小写 section 码应被规范化为大写（#3）。"""
    _fresh_login(driver, base_url)

    # 1) 先建一门课
    driver.get(base_url + "/courses")
    click_button_with_text(driver, "New course")
    code = f"sec{unique()}"
    fill(driver, "#code", code)
    fill(driver, "#name", "Sec Course")
    fill(driver, "#term", "S26")
    click_modal_create(driver)
    wait_table_contains(driver, code.upper())

    # 2) 再建 section
    driver.get(base_url + "/sections")
    click_button_with_text(driver, "New section")
    pick_select(driver, scope_css=".ant-modal", match_text=code.upper())
    fill(driver, "#section_code", "l01")
    click_modal_create(driver)

    wait_table_contains(driver, "L01")
