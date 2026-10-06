import pandas as pd
import plotly.express as px
import streamlit as st

st.set_page_config(
    page_title="Intereuropa - Revizija Računa", page_icon="📦", layout="wide"
)

st.title("📦 Intereuropa: Revizija i Analiza Specifikacija Računa")
st.write(
    "Automatska kontrola troškova prijevoza, dodataka za gorivo i povrata"
    " paleta prema ugovornim uvjetima."
)

# Sidebar za upload
st.sidebar.header("📁 Uvoz podataka")
uploaded_file = st.sidebar.file_uploader(
    "Učitaj Excel specifikaciju računa", type=["xlsx", "xls"]
)


@st.cache_data
def load_data(file):
  df = pd.read_excel(file, header=1)
  return df


# Učitavanje podataka
df = None
if uploaded_file is not None:
  df = load_data(uploaded_file)
else:
  try:
    df = load_data("PZ_INV_1_SPECIFIKACIJA_RACUNA(8).xlsx")
    st.sidebar.success("Učitan zadani uzorak računa.")
  except Exception:
    st.sidebar.info(
        "Molimo učitajte Excel specifikaciju računa u gornjem izborniku."
    )

if df is not None:
  # Osnovne metrike
  st.markdown("---")
  col1, col2, col3, col4 = st.columns(4)

  total_neto = df["Iznos (bezPDV)"].sum()
  total_pdv = df["Iznos PDV"].sum()
  total_sve = df["Iznos ukupno"].sum()
  total_stavki = len(df)

  col1.metric("Ukupno bez PDV-a", f"{total_neto:,.2f} EUR")
  col2.metric("Ukupno PDV", f"{total_pdv:,.2f} EUR")
  col3.metric("Ukupno s PDV-om", f"{total_sve:,.2f} EUR")
  col4.metric("Ukupno stavki", f"{total_stavki}")

  st.markdown("---")

  # Filteri
  st.sidebar.header("🔍 Filteri")
  usluge = (
      ["Sve"] + list(df["Usluga-naziv"].dropna().unique())
      if "Usluga-naziv" in df.columns
      else []
  )
  odabrana_usluga = st.sidebar.selectbox("Filtriraj po usluzi", usluge)

  gradovi = (
      ["Svi"] + list(df["Prim-mjesto"].dropna().unique())
      if "Prim-mjesto" in df.columns
      else []
  )
  odabrani_grad = st.sidebar.selectbox("Filtriraj po primatelju (grad)", gradovi)

  filtered_df = df.copy()
  if odabrana_usluga != "Sve":
    filtered_df = filtered_df[filtered_df["Usluga-naziv"] == odabrana_usluga]
  if odabrani_grad != "Svi":
    filtered_df = filtered_df[filtered_df["Prim-mjesto"] == odabrani_grad]

  # Vizualizacije - svaka u svom odvojenom dijelu za stabilan prikaz
  st.subheader("📊 Analiza troškova")

  c1, c2 = st.columns(2)

  with c1:
    st.markdown("**Troškovi po vrsti usluge**")
    if "Usluga-naziv" in df.columns:
      usluga_grp = (
          df.groupby("Usluga-naziv")["Iznos (bezPDV)"].sum().reset_index()
      )
      fig1 = px.pie(
          usluga_grp,
          names="Usluga-naziv",
          values="Iznos (bezPDV)",
          hole=0.4,
      )
      st.plotly_chart(fig1, use_container_width=True)

  with c2:
    st.markdown("**Top 10 gradova po trošku**")
    if "Prim-mjesto" in df.columns:
      grad_grp = (
          df.groupby("Prim-mjesto")["Iznos (bezPDV)"]
          .sum()
          .reset_index()
          .sort_values(by="Iznos (bezPDV)", ascending=False)
          .head(10)
      )
      fig2 = px.bar(
          grad_grp,
          x="Prim-mjesto",
          y="Iznos (bezPDV)",
          text_auto=".2f",
          labels={"Prim-mjesto": "Grad", "Iznos (bezPDV)": "Iznos (EUR bez PDV)"},
      )
      fig2.update_layout(xaxis_tickangle=-45)
      st.plotly_chart(fig2, use_container_width=True)

  # Tablica podataka
  st.subheader("📋 Pregled stavki računa")
  st.dataframe(filtered_df, use_container_width=True)

  # Export u CSV
  csv = filtered_df.to_csv(index=False).encode("utf-8")
  st.download_button(
      label="📥 Preuzmi filtrirane podatke (CSV)",
      data=csv,
      file_name="intereuropa_analiza.csv",
      mime="text/csv",
  )
