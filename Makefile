build:
	docker-compose build

test: build
	docker build -t nbviewer_test -f Dockerfile.tests .
	docker run -e GITHUB_API_TOKEN nbviewer_test python3 setup.py test
