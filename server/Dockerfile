# Package Building Layer
FROM golang:1.26-bookworm AS builder

WORKDIR /app

COPY go.* ./
RUN go mod download

# Copy local code to the container image.
COPY . ./

# Add extra test builder (if we have test!)

# Build the binary.
RUN go build -v -o server cmd/*.go

# Deploy the final lean build
FROM debian:bookworm-slim

# Install necessary packages
RUN set -x && apt-get update && DEBIAN_FRONTEND=noninteractive apt-get install -y \
    ca-certificates && \
    rm -rf /var/lib/apt/lists/*

# Copy the binary to the production image from the builder stage.
COPY --from=builder /app/server /app/server

# Run the web service on container startup.
CMD ["/app/server"]
