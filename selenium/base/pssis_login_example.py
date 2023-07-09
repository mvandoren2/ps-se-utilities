from selenium import webdriver
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.chrome.service import Service as ChromeService
from selenium.webdriver.common.by import By
from webdriver_manager.chrome import ChromeDriverManager


def main():
    chrome_options = Options()
    chrome_options.add_experimental_option("detach", True)

    # Get latest version of Chrome and use it for the following actions.
    driver = webdriver.Chrome(service=ChromeService(ChromeDriverManager().install()), options=chrome_options)

    driver.get("https://sg1.powerschoolsales.com/admin/pw.html")
    username_field = driver.find_element(By.XPATH, '//*[@id="fieldUsername"]')
    password_field = driver.find_element(By.XPATH, '//*[@id="fieldPassword"]')
    sign_in_button = driver.find_element(By.XPATH, '//*[@id="btnEnter"]')

    username_field.send_keys('mvandoren-admin')
    password_field.send_keys('pwsc2023')
    sign_in_button.click()


if __name__ == '__main__':
    main()
