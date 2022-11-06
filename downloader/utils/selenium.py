from django.conf import settings
from selenium import webdriver
from selenium.webdriver import DesiredCapabilities


def get_driver(folder="", load_images=False):
    """
    获取driver

    :param folder: 唯一文件夹
    :param load_images: 是否加载图片
    :return: WebDriver
    """
    options = webdriver.ChromeOptions()
    prefs = {
        "download.prompt_for_download": False,
        "download.default_directory": "/download/" + folder,  # 下载目录, 需要在docker做映射
        "plugins.always_open_pdf_externally": True,
        "profile.default_content_settings.popups": 0,  # 设置为0，禁止弹出窗口
    }
    # 禁止图片加载
    if not load_images:
        prefs.setdefault("profile.default_content_setting_values.images", 2)
    options.add_experimental_option("prefs", prefs)

    caps = DesiredCapabilities.CHROME
    driver = webdriver.Remote(
        command_executor=settings.SELENIUM_SERVER,
        desired_capabilities=caps,
        options=options,
    )

    return driver
