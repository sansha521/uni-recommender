package main

import (
	"context"
	"log/slog"
	"os"
	"os/signal"
	"syscall"
	"time"

	"github.com/lmittmann/tint"
)

func main() {

	cfg := config{
		addr:    ":8080",
		db:      dbConfig{},
		timeout: 10,
	}

	api := application{
		config: cfg,
	}

	// Define Global Logger
	logger := slog.New(
		tint.NewHandler(
			os.Stdout,
			&tint.Options{
				Level:      slog.LevelInfo,
				TimeFormat: time.Kitchen,
			},
		),
	)
	slog.SetDefault(logger)

	server := api.getServer(api.mount())
	serverErr := make(chan error, 1)
	go func() {
		logger.Info("Server Start Up at", server.Addr)
		serverErr <- server.ListenAndServe()
	}()

	// Signal Context (For Graceful Shutdown)
	signalChan := make(chan os.Signal, 1)
	signal.Notify(signalChan, syscall.SIGINT, syscall.SIGTERM)

	// Check Which Termination signal is received
	select {
	case sig := <-signalChan:
		{
			slog.Info("Shutdown signal", sig.String(), "received! Stopping Services...")
		}
	case err := <-serverErr:
		{
			slog.Error("Fatal Error, Server Failed! Cause: ", err)
			os.Exit(1)
		}
	}
	logger.Info("Server Terminate Signal Received! Stopping Services")

	// Stop all the services like Database here

	// Grace Period for everything to finish up
	shutdownCtx, shutdownRelease := context.WithTimeout(context.Background(), 10*time.Second)
	defer shutdownRelease()

	logger.Info("Shutting Down Server...")

	if err := server.Shutdown(shutdownCtx); err != nil {
		slog.Error("HTTP Server Shutdown error", err)
	}

	slog.Info("Server Graceful Shutdown")
}
