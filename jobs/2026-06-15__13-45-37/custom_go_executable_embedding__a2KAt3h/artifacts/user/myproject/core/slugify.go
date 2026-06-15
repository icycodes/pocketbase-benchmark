package core

import (
	"regexp"
	"strings"
)

var nonAlphaNumRegexp = regexp.MustCompile(`[^a-z0-9]+`)

// Slugify converts a string into a URL-friendly slug.
func Slugify(s string) string {
	s = strings.ToLower(s)
	s = nonAlphaNumRegexp.ReplaceAllString(s, "-")
	s = strings.Trim(s, "-")
	return s
}
