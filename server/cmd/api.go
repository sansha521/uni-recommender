package main

import (
	"net/http"
	"time"

	"github.com/go-chi/chi/v5"
	"github.com/go-chi/chi/v5/middleware"

	"github.com/sansha521/uni-recommender/internal/jsonresponse"
	"github.com/sansha521/uni-recommender/internal/university"
)

type application struct {
	config config

	// logger (application wide logger)
	// logger logger
}

// Collector for all the actual Routers and Handlers for all services
// Add all the handlers and route register here!!
func getHandlers() http.Handler {
	router := chi.NewRouter()

	universityHandler := university.NewHandler(nil)
	university.RegisterRoutes(router, universityHandler)

	return router
}

// Main application router.
// Wraps the router with global middleware and adds /api/v{i} prefix to all endpoints
func (app *application) mount() http.Handler {
	router := chi.NewRouter()

	// Add the middleware stack to the server
	router.Use(middleware.RequestID)
	router.Use(middleware.Logger)
	router.Use(middleware.Recoverer)

	router.Use(middleware.Timeout(60 * time.Second)) // 60 second timout to the endpoints

	// Health Check
	router.Get("/health", func(w http.ResponseWriter, r *http.Request) {

		data := map[string]interface{}{
			"status":  "success",
			"message": "Howdy Fellas!",
		}
		err := jsonresponse.Write(w, http.StatusOK, data)

		if err != nil {
			http.Error(w, err.Error(), http.StatusInternalServerError)
		}

	})

	router.Mount("/api/v1", getHandlers())
	return router
}

// Configures the server based on app configuration and run it!
func (app *application) getServer(h http.Handler) *http.Server {

	server := &http.Server{
		Addr:         app.config.addr,
		Handler:      h,
		WriteTimeout: time.Second * time.Duration(app.config.timeout),
		ReadTimeout:  time.Second * time.Duration(app.config.timeout),
		IdleTimeout:  time.Second * time.Duration(app.config.timeout),
	}
	return server
}

type config struct {
	addr    string
	db      dbConfig
	timeout uint16 // Read/Write Timeout for the server
}

type dbConfig struct {
	dbUri string
}
