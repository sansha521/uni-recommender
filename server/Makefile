APP_NAME=uni-recommender

# Go commands
GO=go

run:
	$(GO) run cmd/*.go

# Build binary
build:
	$(GO) build -o bin/$(APP_NAME) cmd/*.go

# Run compiled binary
start: build
	./bin/$(APP_NAME)

# Format code
fmt:
	$(GO) fmt ./...

# Lint (if you use golangci-lint)
lint:
	golangci-lint run

# Clean build artifacts
clean:
	rm -rf bin/

# Tidy dependencies
tidy:
	$(GO) mod tidy
