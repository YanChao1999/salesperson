.PHONY: test serve docs deploy deploy-down image

test:
	python3 -m unittest discover -s tests -v

serve:
	python3 -m salesperson

docs:
	python3 -m http.server 8080 --directory docs

deploy:
	docker compose --profile deploy up --build -d platform

deploy-down:
	docker compose --profile deploy down

image:
	docker build -t salesperson-platform:latest .
