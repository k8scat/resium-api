python = python
pip = pip

base_image_version = 0.0.2
base_image_name = resium-api-base
base_image_dockerfile = base.Dockerfile

acr_space = resium
acr_username = 1583096683@qq.com
acr_server = registry.cn-hangzhou.aliyuncs.com
acr_password =

image_version = latest
image_name = resium-api
image_dockerfile = Dockerfile

image_tag = $(acr_server)/$(acr_space)/$(image_name):$(image_version)
image_tag_latest = $(acr_server)/$(acr_space)/$(image_name):latest

base_image_tag = $(acr_server)/$(acr_space)/$(base_image_name):$(base_image_version)

dev:
	$(python) manage.py runserver 0:8000

build-image:
	sed -e 's/latest/$(base_image_version)/g' $(image_dockerfile) > Dockerfile.tmp
	docker build \
		--no-cache \
		-f Dockerfile.tmp \
		-t $(image_tag) .
	docker tag $(image_tag) $(image_tag_latest)

install-virtualenv:
	$(pip) install --user virtualenv

new-venv:
	virtualenv -p python3 .venv

enable-venv:
	. .venv/bin/activate

install-mysqlclient:
	yum install -y mysql-devel

install-requirements:
	$(pip) install -r requirements.txt

collectstatic:
	$(python) manage.py collectstatic --settings=resium.settings.prod

createsuperuser:
	python manage.py createsuperuser

migrate-dev:
	python manage.py makemigrations downloader
	python manage.py migrate

migrate-prod:
	python manage.py makemigrations downloader --settings=resium.settings.prod
	python manage.py migrate --settings=resium.settings.prod

login-acr:
	docker login -u $(acr_username) -p $(acr_password) $(acr_server)

logout-acr:
	docker logout $(acr_server)

build-base-image:
	docker build \
		--no-cache \
		-t $(base_image_tag) \
		-f $(base_image_dockerfile) .

build-base-image-arm:
	docker buildx build \
		--no-cache \
		--platform linux/amd64 \
		-t $(base_image_tag) \
		-f $(base_image_dockerfile) .

push-base-image:
	docker push $(base_image_tag)

push-image:
	docker push $(image_tag)
	docker push $(image_tag_latest)

add-admin-user:
	$(python) scripts/add_admin_user.py

format:
	python -m black downloader/
	python -m black resium/
	python -m black scripts/
