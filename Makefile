# Makefile to automate common tasks for the offline patch project

.PHONY: all build compose-up compose-down demo vagrant package deps clean

all: build

# Build all docker images
build:
	./docker/start_all.sh # this builds and starts, so use demo target below

# bring up stack using docker-compose (assumes images already built)
compose-up:
	docker-compose up -d

compose-down:
	docker-compose down -v

# run full demo: generate certs, build, start and exercise API
demo:
	./docker/start_all.sh

# provision Vagrant VM
vagrant:
	vagrant up

# build .deb package
package:
	cd packaging && ./build_deb.sh 0.1.0

# install ansible requirements if needed (not used currently)
deps:
	# place to install any host dependencies
	echo "No dependencies to install"

clean:
	docker-compose down -v
	rm -rf certs
	echo "Cleaned workspace"
