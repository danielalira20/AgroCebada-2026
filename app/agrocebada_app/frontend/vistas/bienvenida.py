import streamlit as st


PASOS = [
    {
        "titulo": "¿Eres agricultor o analista?",
        "descripcion": (
            "AgroCebada tiene dos formas de explorar la información. "
            "Elige la que mejor se adapte a lo que necesitas."
        ),
        "ayuda": (
            "Productor: consulta una parcela y su estimación. "
            "Analista: explora y compara los resultados de distintas parcelas."
        ),
    },
    {
        "titulo": "Así se lee tu estimación",
        "descripcion": (
            "El rendimiento se expresa en toneladas por hectárea (t/ha). "
            "La confianza indica qué tanto respaldo tiene una estimación "
            "y el rango ayuda a interpretar su variación posible."
        ),
        "ayuda": (
            "La confianza no garantiza que se obtenga ese rendimiento. "
            "Los niveles y rangos deben corresponder a los datos disponibles."
        ),
    },
    {
        "titulo": "Qué no hace esta herramienta",
        "descripcion": (
            "AgroCebada estima a partir del valor típico de tu municipio. "
            "No conoce tu manejo agrícola, la variedad que sembraste "
            "ni tu fecha de siembra."
        ),
        "ayuda": (
            "No sustituye una medición en campo ni garantiza "
            "el rendimiento de una cosecha."
        ),
    },
]

@st.dialog("Bienvenido a AgroCebada", width="medium", dismissible=False)

def mostrar_bienvenida():
    """Muestra la bienvenida guiada en un modal de tres pasos."""
    if st.session_state.get("bienvenida_completada", False):
        return

    paso = st.session_state.get("bienvenida_paso", 0)
    paso = max(0, min(paso, len(PASOS) - 1))
    contenido = PASOS[paso]

    st.markdown("""
    <style>
    div[data-testid="stDialog"] div[role="dialog"] {
        max-width: 760px !important;
        width: min(92vw, 760px) !important;
        border-radius: 26px !important;
        border: 1px solid rgba(255,255,255,0.10) !important;
        background:
            linear-gradient(180deg, rgba(255,255,255,0.03), rgba(255,255,255,0.01)),
            rgba(6, 14, 11, 0.96) !important;
        box-shadow:
            0 24px 70px rgba(0,0,0,0.55),
            inset 0 1px 0 rgba(255,255,255,0.06) !important;
    }

    div[data-testid="stDialog"] {
        backdrop-filter: blur(18px) !important;
        -webkit-backdrop-filter: blur(18px) !important;
        background: rgba(5, 12, 9, 0.48) !important;
    }

    div[data-testid="stDialog"] .stProgress > div > div {
        background-color: rgba(255,255,255,0.08) !important;
    }

    div[data-testid="stDialog"] .stButton button[kind="primary"] {
        background: rgba(139, 205, 82, 0.10) !important;
        color: #A3E36B !important;
        border: 2px solid #A3E36B !important;
        border-radius: 16px !important;
        font-weight: 700 !important;
        box-shadow: none !important;
    }

    div[data-testid="stDialog"] .stButton button[kind="primary"]:hover {
        background: rgba(139, 205, 82, 0.20) !important;
        color: #B8F18A !important;
        border-color: #B8F18A !important;
    }

    div[data-testid="stDialog"] .stButton button[kind="secondary"] {
        color: #E7EFE9 !important;
        border: 1px solid rgba(255,255,255,0.12) !important;
        background: rgba(255,255,255,0.03) !important;
    }

    div[data-testid="stDialog"] [data-testid="stInfo"] {
        background: rgba(155,225,93,0.12) !important;
        border: 1px solid rgba(155,225,93,0.22) !important;
        color: #DFF3CF !important;
    }

    div[data-testid="stDialog"] {
        display: flex !important;
        align-items: center !important;
        justify-content: center !important;
    }

    div[data-testid="stDialog"] div[role="dialog"] {
        max-height: 90dvh !important;
        overflow-y: auto !important;
    }

    @media (max-width: 600px) {
        div[data-testid="stDialog"] div[role="dialog"] {
            width: 94vw !important;
            max-height: 88dvh !important;
            border-radius: 18px !important;
        }
    }
    </style>
    """, unsafe_allow_html=True)

    st.progress((paso + 1) / len(PASOS))
    st.caption(f"Paso {paso + 1} de {len(PASOS)}")

    st.subheader(contenido["titulo"])
    st.write(contenido["descripcion"])
    st.markdown(
        f"""
        <div style="
            background: rgba(155, 225, 93, 0.10);
            border: 1px solid rgba(155, 225, 93, 0.25);
            border-left: 4px solid #9BE15D;
            border-radius: 12px;
            padding: 14px 18px;
            color: #DDEBD5;
            line-height: 1.6;
            margin: 14px 0 20px;
        ">
            {contenido["ayuda"]}
        </div>
        """,
        unsafe_allow_html=True,
    )

    if paso == 0:
        vista_elegida = st.radio(
            "¿Cómo quieres explorar AgroCebada?",
            ["Agricultor", "Analista"],
            horizontal=True,
            key="bienvenida_tipo_usuario",
        )

        st.session_state["bienvenida_vista_elegida"] = (
            "Agricultor" if vista_elegida == "Agricultor" else "Analista"
        )

    anterior, siguiente = st.columns(2)

    with anterior:
        if paso > 0 and st.button("← Anterior", use_container_width=True):
            st.session_state["bienvenida_paso"] = paso - 1
            st.rerun(scope="fragment")

    with siguiente:
        etiqueta = "Entrar a AgroCebada →" if paso == 2 else "Siguiente →"

        if st.button(etiqueta, type="primary", use_container_width=True):
            if paso == 2:
                st.session_state["vista"] = st.session_state.get(
                    "bienvenida_vista_elegida", "Agricultor"
                )
                st.session_state["bienvenida_completada"] = True
                st.rerun()
            else:
                st.session_state["bienvenida_paso"] = paso + 1
                st.rerun(scope="fragment")

    if st.button("Omitir introducción"):
        st.session_state["bienvenida_completada"] = True
        st.rerun()

    return False