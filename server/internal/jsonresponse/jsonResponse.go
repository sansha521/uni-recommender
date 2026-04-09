package jsonresponse

import (
	"encoding/json"
	"net/http"
)

func Write(w http.ResponseWriter, httpStatus int, data any) error {
	w.Header().Set("Content-Type", "application/json")
	w.WriteHeader(httpStatus)
	return json.NewEncoder(w).Encode(data)
}
