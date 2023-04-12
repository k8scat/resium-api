python = python
pip = pip

cr_user = k8scat
cr_server = ghcr.io
cr_password =

image_version = latest
image_name = resium-api
image_dockerfile = Dockerfile

image_tag = $(cr_server)/$(cr_user)/$(image_name):$(image_version)
image_tag_latest = $(cr_server)/$(cr_user)/$(image_name):latest

.PHONY: run-dev
run-dev:
	$(python) manage.py runserver 0:8000

.PHONY: build-image
build-image:
	docker build \
		--no-cache \
		-f Dockerfile \
		-t $(image_tag) .
	docker tag $(image_tag) $(image_tag_latest)

.PHONY: install-virtualenv
install-virtualenv:
	$(pip) install --user virtualenv

.PHONY: create-venv
create-venv:
	virtualenv -p python3 .venv

.PHONY: install-requirements
install-requirements:
	$(pip) install -r requirements.txt

.PHONY: install-requirements-dev
install-requirements-dev:
	$(pip) install -r requirements-dev.txt

.PHONY: collectstatic
collectstatic:
	$(python) manage.py collectstatic

.PHONY: createsuperuser
createsuperuser:
	python manage.py createsuperuser

.PHONY: migrate-dev
migrate-dev:
	python manage.py makemigrations downloader
	python manage.py migrate

.PHONY: migrate-prod
migrate-prod:
	python manage.py makemigrations downloader --settings=resium.settings.prod
	python manage.py migrate --settings=resium.settings.prod

.PHONY: login-cr
login-cr:
	docker login -u $(cr_user) -p $(cr_password) $(cr_server)

.PHONY: login-cr
logout-cr:
	docker logout $(cr_server)

.PHONY: push-image
push-image:
	docker push $(image_tag)
	docker push $(image_tag_latest)

.PHONY: format
format: install-requirements-dev
	python -m black downloader/
	python -m black resium/
