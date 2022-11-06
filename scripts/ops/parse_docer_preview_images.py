# -*- coding: utf-8 -*-

"""
@author: hsowan <hsowan.me@gmail.com>
@date: 2020/3/31

"""
import os
import django

os.environ.setdefault("DJANGO_SETTINGS_MODULE", "resium.settings.prod")
django.setup()

from downloader.models import DocerPreviewImage, Resource


from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.support.wait import WebDriverWait


if __name__ == "__main__":
    resources = Resource.objects.filter(url__icontains="docer.com").all()
    for resource in resources:
        resource_url = resource.url
        if DocerPreviewImage.objects.filter(resource_url=resource_url).count() < 4:
            print(resource_url)
        if DocerPreviewImage.objects.filter(resource_url=resource_url).count() == 0:
            driver = webdriver.Chrome()
            try:
                driver.get(resource_url)
                all_images = WebDriverWait(driver, 5).until(
                    EC.presence_of_all_elements_located(
                        (By.XPATH, '//ul[@class="preview__img-list"]//img')
                    )
                )
                preview_images = []
                preview_image_models = []
                for image in all_images:
                    image_url = image.get_attribute("data-src")
                    image_alt = image.get_attribute("alt")
                    preview_images.append({"url": image_url, "alt": image_alt})
                    preview_image_models.append(
                        DocerPreviewImage(
                            resource_url=resource_url, url=image_url, alt=image_alt
                        )
                    )
                DocerPreviewImage.objects.bulk_create(preview_image_models)
            finally:
                driver.close()
