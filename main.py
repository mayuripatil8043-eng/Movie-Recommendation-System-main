import os
import requests

from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware


# =========================================================
# CONFIG
# =========================================================

TMDB_API_KEY = os.getenv("TMDB_API_KEY")

TMDB_BASE_URL = "https://api.themoviedb.org/3"
TMDB_IMAGE_URL = "https://image.tmdb.org/t/p/w500"
TMDB_BACKDROP_URL = "https://image.tmdb.org/t/p/w1280"


# =========================================================
# FASTAPI APP
# =========================================================

app = FastAPI(
    title="Movie Recommendation API",
    description="Movie Recommendation System API",
    version="1.0.0"
)


# =========================================================
# CORS
# =========================================================

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


# =========================================================
# TMDB API CHECK
# =========================================================

def check_api_key():

    if not TMDB_API_KEY:

        raise HTTPException(
            status_code=500,
            detail="TMDB_API_KEY is not configured."
        )


# =========================================================
# TMDB REQUEST
# =========================================================

def tmdb_get(endpoint, params=None):

    check_api_key()

    if params is None:
        params = {}

    params["api_key"] = TMDB_API_KEY

    try:

        response = requests.get(
            f"{TMDB_BASE_URL}{endpoint}",
            params=params,
            timeout=20
        )

    except requests.RequestException as e:

        raise HTTPException(
            status_code=503,
            detail=f"TMDB connection failed: {e}"
        )

    if response.status_code != 200:

        raise HTTPException(
            status_code=response.status_code,
            detail=response.text[:500]
        )

    return response.json()


# =========================================================
# CONVERT TMDB MOVIE TO CARD
# =========================================================

def movie_card(movie):

    poster_path = movie.get("poster_path")

    return {
        "tmdb_id": movie.get("id"),

        "title": (
            movie.get("title")
            or movie.get("name")
            or "Untitled"
        ),

        "poster_url": (
            f"{TMDB_IMAGE_URL}{poster_path}"
            if poster_path
            else None
        ),

        "release_date": (
            movie.get("release_date")
            or ""
        ),

        "overview": (
            movie.get("overview")
            or ""
        ),

        "vote_average": (
            movie.get("vote_average")
            or 0
        ),

        "genre_ids": (
            movie.get("genre_ids")
            or []
        )
    }


# =========================================================
# HOME
# =========================================================

@app.get("/")
def root():

    return {
        "status": "online",
        "message": "🎬 Movie Recommendation API is running"
    }


# =========================================================
# HEALTH CHECK
# =========================================================

@app.get("/health")
def health():

    return {
        "status": "healthy",
        "tmdb_configured": bool(TMDB_API_KEY)
    }


# =========================================================
# TMDB SEARCH
# =========================================================

@app.get("/tmdb/search")
def search_movies(
    query: str,
    page: int = 1
):

    if not query.strip():

        return []

    data = tmdb_get(
        "/search/movie",
        {
            "query": query.strip(),
            "page": page,
            "include_adult": False
        }
    )

    return [
        movie_card(movie)
        for movie in data.get("results", [])
    ]


# =========================================================
# HOME FEED
# =========================================================

@app.get("/home")
def home(
    category: str = "trending",
    limit: int = 24
):

    allowed_categories = [
        "trending",
        "popular",
        "top_rated",
        "now_playing",
        "upcoming"
    ]

    if category not in allowed_categories:

        category = "trending"

    limit = max(
        1,
        min(limit, 40)
    )

    # Trending
    if category == "trending":

        data = tmdb_get(
            "/trending/movie/week"
        )

    # Other categories
    else:

        data = tmdb_get(
            f"/movie/{category}"
        )

    movies = [
        movie_card(movie)
        for movie in data.get(
            "results",
            []
        )
    ]

    return movies[:limit]


# =========================================================
# MOVIE DETAILS
# =========================================================

@app.get("/movie/id/{tmdb_id}")
def movie_details(
    tmdb_id: int
):

    data = tmdb_get(
        f"/movie/{tmdb_id}"
    )

    poster_path = data.get(
        "poster_path"
    )

    backdrop_path = data.get(
        "backdrop_path"
    )

    return {

        "tmdb_id": data.get("id"),

        "title": data.get("title"),

        "overview": (
            data.get("overview")
            or ""
        ),

        "release_date": (
            data.get("release_date")
            or ""
        ),

        "runtime": data.get(
            "runtime"
        ),

        "vote_average": data.get(
            "vote_average",
            0
        ),

        "vote_count": data.get(
            "vote_count",
            0
        ),

        "poster_url": (
            f"{TMDB_IMAGE_URL}{poster_path}"
            if poster_path
            else None
        ),

        "backdrop_url": (
            f"{TMDB_BACKDROP_URL}{backdrop_path}"
            if backdrop_path
            else None
        ),

        "genres": [
            {
                "id": genre.get("id"),
                "name": genre.get("name")
            }
            for genre in data.get(
                "genres",
                []
            )
        ],

        "homepage": data.get(
            "homepage"
        )
    }


# =========================================================
# GENRE RECOMMENDATIONS
# =========================================================

@app.get("/recommend/genre")
def genre_recommendations(
    tmdb_id: int,
    limit: int = 18
):

    movie = tmdb_get(
        f"/movie/{tmdb_id}"
    )

    genres = movie.get(
        "genres",
        []
    )

    if not genres:

        return []

    genre_id = genres[0].get(
        "id"
    )

    if not genre_id:

        return []

    data = tmdb_get(
        "/discover/movie",
        {
            "with_genres": genre_id,
            "sort_by": "popularity.desc",
            "include_adult": False,
            "page": 1
        }
    )

    recommendations = []

    for item in data.get(
        "results",
        []
    ):

        if item.get("id") == tmdb_id:
            continue

        recommendations.append(
            movie_card(item)
        )

        if len(
            recommendations
        ) >= limit:

            break

    return recommendations


# =========================================================
# SIMILAR MOVIES
# =========================================================

@app.get("/movie/search")
def movie_search(
    query: str,
    tfidf_top_n: int = 12,
    genre_limit: int = 12
):

    if not query.strip():

        return {
            "tfidf_recommendations": [],
            "genre_recommendations": []
        }


    # -----------------------------------------------------
    # SEARCH MOVIE
    # -----------------------------------------------------

    search_data = tmdb_get(
        "/search/movie",
        {
            "query": query.strip(),
            "include_adult": False
        }
    )

    results = search_data.get(
        "results",
        []
    )

    if not results:

        return {
            "tfidf_recommendations": [],
            "genre_recommendations": []
        }


    selected_movie = results[0]

    selected_id = selected_movie.get(
        "id"
    )


    # -----------------------------------------------------
    # SIMILAR MOVIES
    # -----------------------------------------------------

    similar_data = tmdb_get(
        f"/movie/{selected_id}/similar",
        {
            "page": 1
        }
    )

    similar_movies = []

    for movie in similar_data.get(
        "results",
        []
    ):

        if movie.get("id") == selected_id:
            continue

        similar_movies.append(
            {
                "title": movie.get(
                    "title"
                ),

                "tmdb": movie_card(
                    movie
                )
            }
        )

        if len(
            similar_movies
        ) >= tfidf_top_n:

            break


    # -----------------------------------------------------
    # GENRE RECOMMENDATIONS
    # -----------------------------------------------------

    details = tmdb_get(
        f"/movie/{selected_id}"
    )

    genres = details.get(
        "genres",
        []
    )

    genre_movies = []

    if genres:

        genre_id = genres[0].get(
            "id"
        )

        if genre_id:

            genre_data = tmdb_get(
                "/discover/movie",
                {
                    "with_genres": genre_id,
                    "sort_by": "popularity.desc",
                    "include_adult": False,
                    "page": 1
                }
            )

            for movie in genre_data.get(
                "results",
                []
            ):

                if movie.get(
                    "id"
                ) == selected_id:

                    continue

                genre_movies.append(
                    movie_card(movie)
                )

                if len(
                    genre_movies
                ) >= genre_limit:

                    break


    # -----------------------------------------------------
    # FINAL RESPONSE
    # -----------------------------------------------------

    return {

        "tfidf_recommendations":
            similar_movies,

        "genre_recommendations":
            genre_movies
    }