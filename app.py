import pandas as pd
import plotly.express as px
import streamlit as st

st.set_page_config(
    page_title="Intereuropa - Revizija i Analiza Računa",
    page_icon="📦",
    layout="wide",
)

st.title(
    "📦 Intereuropa: Automatska Revizija i Usporedba Računa s Ugovornim Cijenama"
)
st.write(
    "Napredna kontrola troškova prijevoza, dodataka za gorivo i paleta prema"
    " službenom ugovornom cjeniku."
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


# Definicija ugovornih cjenika po zonama
# Paketi (Expressne i cargo pošiljke)
package_prices = {
    2: (3.37, 4.45, 6.13),
    5: (3.83, 5.06, 7.05),
    10: (4.68, 6.13, 8.35),
    15: (5.52, 7.28, 9.81),
    20: (6.36, 8.35, 11.19),
    25: (7.13, 9.50, 12.88),
    30: (8.05, 10.65, 13.95),
    35: (10.23, 13.59, 16.87),
    40: (11.25, 14.92, 19.45),
    45: (12.19, 16.17, 20.78),
    50: (13.20, 17.50, 22.65),
    75: (18.28, 24.37, 29.84),
    100: (22.11, 29.37, 35.46),
    150: (24.03, 31.99, 38.19),
    200: (25.70, 34.22, 40.66),
    250: (28.96, 38.51, 46.07),
    300: (32.07, 42.81, 50.29),
    350: (37.80, 50.29, 58.88),
    400: (43.37, 57.77, 67.48),
    450: (47.48, 63.12, 74.06),
    500: (50.64, 67.50, 78.44),
    600: (58.10, 77.38, 89.30),
    700: (69.52, 92.62, 106.72),
}
package_extra_100 = (10.45, 13.78, 17.42)

# Palete (Euro paletne pošiljke)
pallet_prices = {
    200: (23.01, 30.71, 36.46),
    250: (26.01, 34.60, 41.41),
    300: (28.77, 38.41, 45.13),
    350: (34.48, 45.95, 53.78),
    400: (39.51, 52.71, 61.62),
    450: (42.65, 56.75, 66.49),
    500: (46.34, 61.62, 71.61),
    600: (53.06, 70.69, 81.60),
    700: (63.47, 84.54, 97.47),
}
pallet_extra_100 = (9.49, 12.68, 15.95)


def odredi_zonu(postanski_broj):
  try:
    pb = int(postanski_broj)
  except:
    return 1
  # Zona 1: Zagreb i okolica (10xxx)
  if 10000 <= pb <= 10450:
    return 0  # Index 0 za Zonu 1
  # Zona 3: Izrazito udaljena mjesta
  elif pb in [53200, 20260, 20290]:
    return 2  # Index 2 za Zonu 3
  else:
    return 1  # Index 1 za Zonu 2 (veći gradovi)


def izracunaj_ugovornu_cijenu(row):
  usluga = str(row.get("Usluga-naziv", ""))
  tezina = row.get("Vred.osn./količ.", 0)
  try:
    tezina = float(tezina)
  except:
    tezina = 0.0

  pb = row.get("Prim.-pošt.br.", 10000)
  zone_idx = odredi_zonu(pb)

  # Provjera otoka / južne destinacije (ZIP počinje s 20 -> +50% na Zonu 2)
  is_island_or_south = str(pb).startswith("20")

  cijena = 0.0

  if "EXPRESS" in usluga or "PAKET" in usluga or "PRIJEVOZ" in usluga:
    thresholds = sorted(package_prices.keys())
    if tezina <= thresholds[0]:
      t = thresholds[0]
    else:
      t = thresholds[-1]
      for th in thresholds:
        if tezina <= th:
          t = th
          break
      if tezina > thresholds[-1]:
        base_price = package_prices[700][zone_idx]
        extra_blocks = max(
            0.0, ((tezina - 700) + 99.99) // 100
        )  # za svaka započeta 100kg
        cijena = base_price + extra_blocks * package_extra_100[zone_idx]
    if cijena == 0.0:
      cijena = package_prices[t][zone_idx]

  elif "PALET" in usluga:
    thresholds = sorted(pallet_prices.keys())
    if tezina <= thresholds[0]:
      t = thresholds[0]
    else:
      t = thresholds[-1]
      for th in thresholds:
        if tezina <= th:
          t = th
          break
      if tezina > thresholds[-1]:
        base_price = pallet_prices[700][zone_idx]
        extra_blocks = max(0.0, ((tezina - 700) + 99.99) // 100)
        cijena = base_price + extra_blocks * pallet_extra_100[zone_idx]
    if cijena == 0.0:
      cijena = pallet_prices[t][zone_idx]

  elif "VRAĆANJE PALET" in usluga:
    cijena = 2.00  # Ugovorena cijena povrata palete

  elif "GORIVO" in usluga:
    cijena = 0.0

  if is_island_or_south and zone_idx == 1:
    cijena = cijena * 1.5  # +50% za otoke/Dubrovačku regiju

  return round(cijena, 2)


if df is not None:
  # Izračun ugovornih cijena i razlika za svaku stavku
  df["Ugovorna_Cijena"] = df.apply(izracunaj_ugovornu_cijenu, axis=1)
  df["Razlika_Preplaceno"] = df.apply(
      lambda r: (
          r["Iznos (bezPDV)"] - r["Ugovorna_Cijena"]
          if "PRIJEVOZ" in str(r.get("Usluga-naziv", ""))
          or "PALET" in str(r.get("Usluga-naziv", ""))
          else 0
      ),
      axis=1,
  )

  # Osnovne metrike
  st.markdown("---")
  col1, col2, col3, col4 = st.columns(4)

  total_neto = df["Iznos (bezPDV)"].sum()
  total_ugovor = df["Ugovorna_Cijena"].sum()
  total_razlika = df[df["Razlika_Preplaceno"] > 0]["Razlika_Preplaceno"].sum()
  total_stavki = len(df)

  col1.metric("Ukupno naplaćeno (bez PDV)", f"{total_neto:,.2f} EUR")
  col2.metric("Procjena po cjeniku", f"{total_ugovor:,.2f} EUR")
  col3.metric("Uočeno preplaćeno", f"{total_razlika:,.2f} EUR", delta_color="inverse")
  col4.metric("Ukupno stavki", f"{total_stavki}")

  st.markdown("---")

  # Filteri u sidebar-u
  st.sidebar.header("🔍 Filteri i Revizija")
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

  samo_preplaceno = st.sidebar.checkbox(
      "Prikaži samo sumnjive / preplaćene stavke"
  )

  filtered_df = df.copy()
  if odabrana_usluga != "Sve":
    filtered_df = filtered_df[filtered_df["Usluga-naziv"] == odabrana_usluga]
  if odabrani_grad != "Svi":
    filtered_df = filtered_df[filtered_df["Prim-mjesto"] == odabrani_grad]
  if samo_preplaceno:
    filtered_df = filtered_df[filtered_df["Razlika_Preplaceno"] > 0]

  # Vizualizacije
  st.subheader("📊 Vizualna analiza troškova")
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
          labels={"Prim-mjesto": "Grad", "Iznos (bezPDV)": "Iznos (EUR bez PDV)"},
      )
      fig2.update_layout(xaxis_tickangle=-45)
      st.plotly_chart(fig2, use_container_width=True)

  # Detaljna tablica revizije
  st.subheader("📋 Detaljna tablica revizije i usporedbe s cjenikom")
  st.dataframe(
      filtered_df[[
          "Br.rač.",
          "Dat.rač.",
          "Usluga-naziv",
          "Prim-mjesto",
          "Prim.-pošt.br.",
          "Vred.osn./količ.",
          "JM",
          "Iznos (bezPDV)",
          "Ugovorna_Cijena",
          "Razlika_Preplaceno",
      ]],
      use_container_width=True,
  )

  # Export u CSV
  csv = filtered_df.to_csv(index=False).encode("utf-8")
  st.download_button(
      label="📥 Preuzmi izvještaj revizije (CSV)",
      data=csv,
      file_name="intereuropa_revizija_izvjestaj.csv",
      mime="text/csv",
  )
