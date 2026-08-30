import requests
import streamlit as st


# =========================================================
# CONFIG
# =========================================================

API_BASE = "https://movie-rec-466x.onrender.com"

st.set_page_config(
    page_title="Movie Recommender",
    page_icon="🎬",
    layout="wide"
)


# =========================================================
# CSS
# =========================================================

st.markdown(
    """
    <style>

    .block-container {
        padding-top: 1rem;
        padding-bottom: 2rem;
        max-width: 1400px;
    }

    .subtitle {
        color: #6b7280;
        font-size: 0.95rem;
    }

    .movie-title {
        text-align: center;
        font-size: 0.95rem;
        font-weight: 600;
        margin-top: 8px;
        min-height: 45px;
    }

    .movie-rating {
        text-align: center;
        color: #6b7280;
        font-size: 0.85rem;
    }

    </style>
    """,
    unsafe_allow_html=True
)


# =========================================================
# SESSION STATE
# =========================================================

if "page" not in st.session_state:
    st.session_state.page = "home"

if "selected_movie_id" not in st.session_state:
    st.session_state.selected_movie_id = None


# =========================================================
# NAVIGATION
# =========================================================

def open_movie(tmdb_id):

    st.session_state.selected_movie_id = int(
        tmdb_id
    )

    st.session_state.page = "details"

    st.rerun()


def go_home():

    st.session_state.page = "home"

    st.session_state.selected_movie_id = None

    st.rerun()


# =========================================================
# API FUNCTION
# =========================================================

@st.cache_data(ttl=120)
def api_get(
    endpoint,
    params=None
):

    try:

        response = requests.get(
            f"{API_BASE}{endpoint}",
            params=params,
            timeout=30
        )

        if response.status_code != 200:

            return None, (
                f"HTTP {response.status_code}: "
                f"{response.text[:300]}"
            )

        return response.json(), None

    except Exception as e:

        return None, str(e)


# =========================================================
# MOVIE CARD GRID
# =========================================================

def show_movies(
    movies,
    columns=6,
    key_prefix="movies"
):

    if not movies:

        st.info(
            "No movies found."
        )

        return

    cols = st.columns(
        columns
    )

    for index, movie in enumerate(movies):

        tmdb_id = (
            movie.get("tmdb_id")
            or movie.get("id")
        )

        title = (
            movie.get("title")
            or "Untitled"
        )

        poster = movie.get(
            "poster_url"
        )

        rating = movie.get(
            "vote_average"
        )

        with cols[
            index % columns
        ]:

            # Poster
            if poster:

                st.image(
                    poster,
                    use_container_width=True
                )

            else:

                st.info(
                    "🖼️ No poster"
                )

            # Open
            if tmdb_id:

                if st.button(
                    "🎬 Open",
                    key=(
                        f"{key_prefix}_"
                        f"{index}_"
                        f"{tmdb_id}"
                    ),
                    use_container_width=True
                ):

                    open_movie(
                        tmdb_id
                    )

            # Title
            st.markdown(
                f"""
                <div class="movie-title">
                    {title}
                </div>
                """,
                unsafe_allow_html=True
            )

            # Rating
            if rating:

                st.markdown(
                    f"""
                    <div class="movie-rating">
                        ⭐ {float(rating):.1f}/10
                    </div>
                    """,
                    unsafe_allow_html=True
                )


# =========================================================
# SIDEBAR
# =========================================================

with st.sidebar:

    st.markdown(
        "## 🎬 Movie Recommender"
    )

    if st.button(
        "🏠 Home",
        use_container_width=True
    ):

        go_home()

    st.markdown("---")

    category = st.selectbox(
        "Home Category",
        [
            "trending",
            "popular",
            "top_rated",
            "now_playing",
            "upcoming"
        ]
    )

    columns = st.slider(
        "Movies per row",
        4,
        8,
        6
    )


# =========================================================
# HOME
# =========================================================

if st.session_state.page == "home":

    st.title(
        "🎬 Movie Recommender"
    )

    st.markdown(
        """
        <div class="subtitle">
        Search your favourite movie and discover
        similar movies 🍿
        </div>
        """,
        unsafe_allow_html=True
    )

    st.divider()

    # -----------------------------------------------------
    # SEARCH
    # -----------------------------------------------------

    query = st.text_input(
        "🔎 Search Movie",
        placeholder=(
            "Example: Avengers, Batman, Titanic..."
        )
    )

    if query.strip():

        if len(query.strip()) < 2:

            st.warning(
                "Please type at least 2 characters."
            )

        else:

            movies, error = api_get(
                "/tmdb/search",
                {
                    "query": query.strip()
                }
            )

            if error:

                st.error(
                    f"Search failed: {error}"
                )

            elif movies:

                st.markdown(
                    "### 🔎 Search Results"
                )

                # Suggestion dropdown
                movie_names = [
                    movie["title"]
                    for movie in movies
                    if movie.get("title")
                ]

                selected = st.selectbox(
                    "🎯 Quick Select",
                    [
                        "-- Select movie --"
                    ] + movie_names
                )

                if (
                    selected
                    != "-- Select movie --"
                ):

                    selected_movie = next(
                        (
                            movie
                            for movie in movies
                            if movie["title"]
                            == selected
                        ),
                        None
                    )

                    if selected_movie:

                        open_movie(
                            selected_movie[
                                "tmdb_id"
                            ]
                        )

                show_movies(
                    movies,
                    columns=columns,
                    key_prefix="search"
                )

            else:

                st.info(
                    "No movies found."
                )

    # -----------------------------------------------------
    # HOME FEED
    # -----------------------------------------------------

    st.divider()

    st.markdown(
        f"""
        ### 🏠 {
            category.replace(
                "_",
                " "
            ).title()
        }
        """
    )

    home_movies, error = api_get(
        "/home",
        {
            "category": category,
            "limit": 24
        }
    )

    if error:

        st.error(
            f"Home feed failed: {error}"
        )

    elif home_movies:

        show_movies(
            home_movies,
            columns=columns,
            key_prefix="home"
        )


# =========================================================
# DETAILS PAGE
# =========================================================

elif st.session_state.page == "details":

    movie_id = (
        st.session_state.selected_movie_id
    )

    if not movie_id:

        st.warning(
            "No movie selected."
        )

        if st.button(
            "← Home"
        ):

            go_home()

        st.stop()


    # -----------------------------------------------------
    # BACK BUTTON
    # -----------------------------------------------------

    if st.button(
        "← Back to Home"
    ):

        go_home()


    # -----------------------------------------------------
    # DETAILS API
    # -----------------------------------------------------

    movie, error = api_get(
        f"/movie/id/{movie_id}"
    )

    if error:

        st.error(
            f"Could not load movie: {error}"
        )

        st.stop()


    # -----------------------------------------------------
    # DETAILS
    # -----------------------------------------------------

    st.title(
        f"🎬 {movie.get('title', 'Movie')}"
    )

    left, right = st.columns(
        [1, 2],
        gap="large"
    )

    with left:

        poster = movie.get(
            "poster_url"
        )

        if poster:

            st.image(
                poster,
                use_container_width=True
            )

        else:

            st.info(
                "🖼️ Poster not available"
            )


    with right:

        release = (
            movie.get(
                "release_date"
            )
            or "-"
        )

        rating = movie.get(
            "vote_average"
        )

        runtime = movie.get(
            "runtime"
        )

        genres = movie.get(
            "genres",
            []
        )

        genre_names = ", ".join(
            [
                g["name"]
                for g in genres
                if g.get("name")
            ]
        )

        st.markdown(
            f"**📅 Release:** {release}"
        )

        if rating:

            st.markdown(
                f"**⭐ Rating:** "
                f"{float(rating):.1f}/10"
            )

        if runtime:

            st.markdown(
                f"**⏱️ Runtime:** "
                f"{runtime} minutes"
            )

        st.markdown(
            f"**🎭 Genres:** "
            f"{genre_names or '-'}"
        )

        st.divider()

        st.markdown(
            "### 📖 Overview"
        )

        st.write(
            movie.get(
                "overview"
            )
            or "No overview available."
        )


    # -----------------------------------------------------
    # BACKDROP
    # -----------------------------------------------------

    backdrop = movie.get(
        "backdrop_url"
    )

    if backdrop:

        st.divider()

        st.markdown(
            "### 🖼️ Backdrop"
        )

        st.image(
            backdrop,
            use_container_width=True
        )


    # -----------------------------------------------------
    # RECOMMENDATIONS
    # -----------------------------------------------------

    st.divider()

    st.markdown(
        "## 🍿 Recommended Movies"
    )


    recommendations, error = api_get(
        "/movie/search",
        {
            "query": movie.get(
                "title",
                ""
            ),
            "tfidf_top_n": 12,
            "genre_limit": 12
        }
    )


    if error:

        st.error(
            f"Could not load recommendations: "
            f"{error}"
        )

    elif recommendations:

        # -------------------------------------------------
        # SIMILAR
        # -------------------------------------------------

        similar = []

        for item in recommendations.get(
            "tfidf_recommendations",
            []
        ):

            tmdb = item.get(
                "tmdb",
                {}
            )

            if tmdb:

                similar.append(
                    tmdb
                )

        if similar:

            st.markdown(
                "### 🔎 Similar Movies"
            )

            show_movies(
                similar,
                columns=columns,
                key_prefix="similar"
            )


        # -------------------------------------------------
        # GENRE
        # -------------------------------------------------

        genre_movies = recommendations.get(
            "genre_recommendations",
            []
        )

        if genre_movies:

            st.markdown(
                "### 🎭 More Like This"
            )

            show_movies(
                genre_movies,
                columns=columns,
                key_prefix="genre"
            )