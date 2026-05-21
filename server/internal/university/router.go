package university

import "github.com/go-chi/chi/v5"

func RegisterRoutes(r chi.Router, h *handler) {
	r.Route("/university", func(r chi.Router) {
		r.Get("/list", h.ListUniversity)
	})
}
