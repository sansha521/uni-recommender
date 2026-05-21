package university

import (
	"log/slog"
	"net/http"

	"github.com/sansha521/uni-recommender/internal/jsonresponse"
)

type handler struct {
	service Service
}

func NewHandler(service Service) *handler {
	return &handler{
		service: service,
	}
}

func (h *handler) ListUniversity(w http.ResponseWriter, r *http.Request) {
	// For Handler -> Call service which does business logic
	// Returns JSON response
	slog.Info("Hello!!!!")

	data := map[string]string{
		"message": "Hello",
	}
	jsonresponse.Write(w, http.StatusOK, data)
}
