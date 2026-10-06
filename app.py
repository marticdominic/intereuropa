import io
import pandas as pd
import plotly.express as px
import streamlit as st

st.set_page_config(
    page_title="Sustav za Kontrolu i Analizu Logističkih Računa",
    page_icon="📦",
    layout="wide",
)

st.title("📦 Sustav za Kontrolu i Analizu Logističkih Računa")
st.write(
    "Automatska kontrola troškova prijevoza, dodataka za gorivo i dodatnih"
    " usluga prema ugovornim uvjetima."
)

# Sidebar za upload
st.sidebar.header("📁 Uvoz podataka")
uploaded_file = st.sidebar.file_uploader(
    "Učitaj Excel ili CSV tablicu s pošiljkama", type=["xlsx", "xls", "csv"]
)


@st.cache_data
def load_data(file):
  if file.name.endswith(".csv"):
    df = pd.read_csv(file)
  else:
    df = pd.read_excel(file, header=1)
  return df


# Učitavanje podataka
df = None
if uploaded_file is not None:
  df = load_data(uploaded_file)
  st.sidebar.success("Tablica uspješno učitana!")
else:
  try:
    df = load_data("PZ_INV_1_SPECIFIKACIJA_RACUNA(8).xlsx")
    st.sidebar.success("Učitan zadani uzorak računa.")
  except Exception:
    st.sidebar.info("Molimo učitajte Excel specifikaciju računa.")


# Definicija ugovornih cjenika po zonama
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
  if 10000 <= pb <= 10450:
    return 0  # Zona 1
  elif pb in [53200, 20260, 20290]:
    return 2  # Zona 3
  else:
    return 1  # Zona 2


def izracunaj_ugovornu_cijenu(row):
  usluga = str(row.get("Usluga-naziv", "")).upper()
  tezina = row.get("Vred.osn./količ.", 0)
  try:
    tezina = float(tezina)
  except:
    tezina = 0.0

  pb = row.get("Prim.-pošt.br.", 10000)
  zone_idx = odredi_zonu(pb)
  is_island_or_south = str(pb).startswith("20")

  cijena = 0.0

  # Prepoznavanje vraćanja paleta (fiksno 2.00 EUR po komadu/količini)
  if "VRAĆANJE" in usluga and "PALET" in usluga:
    kolicina = tezina if tezina > 0 else 1.0
    return round(2.00 * kolicina, 2)

  elif "EXPRESS" in usluga or "PAKET" in usluga or "PRIJEVOZ" in usluga:
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
        extra_blocks = max(0.0, ((tezina - 700) + 99.99) // 100)
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

  elif "GORIVO" in usluga:
    cijena = 0.0

  if is_island_or_south and zone_idx == 1 and not ("VRAĆANJE" in usluga):
    cijena = cijena * 1.5

  return round(cijena, 2)


def izracunaj_radne_dane(row):
  try:
    dt_odlazak = pd.to_datetime(row.get("Odlazak"))
    dt_dostava = pd.to_datetime(row.get("Dostava"))
    if pd.isna(dt_odlazak) or pd.isna(dt_dostava):
      return None
    radni_dani = pd.bdate_range(
        start=dt_odlazak.normalize(), end=dt_dostava.normalize()
    )
    broj_dana = max(0, len(radni_dani) - 1)
    return int(broj_dana)
  except:
    return None


if df is not None:
  # Izračun cijena i razlika
  df["Ugovorna_Cijena"] = df.apply(izracunaj_ugovornu_cijenu, axis=1)
  df["Razlika_Preplaceno"] = df.apply(
      lambda r: (
          r["Iznos (bezPDV)"] - r["Ugovorna_Cijena"]
          if "PRIJEVOZ" in str(r.get("Usluga-naziv", ""))
          or "PALET" in str(r.get("Usluga-naziv", ""))
          or "VRAĆANJE" in str(r.get("Usluga-naziv", ""))
          else 0
      ),
      axis=1,
  )

  # Izračun rokova isporuke
  if "Odlazak" in df.columns and "Dostava" in df.columns:
    df["Radni_Dani_Isporuke"] = df.apply(izracunaj_radne_dane, axis=1)

    def provjeri_sla(row):
      pb = str(row.get("Prim.-pošt.br.", ""))
      zone_idx = odredi_zonu(pb)
      is_island_or_south = pb.startswith("20")
      dozvoljeno_dana = 3 if (is_island_or_south or zone_idx == 2) else 2
      st_dani = row.get("Radni_Dani_Isporuke")
      if pd.isna(st_dani):
        return "Nepoznato"
      if st_dani <= dozvoljeno_dana:
        return f"{int(st_dani)} rad. dana (U roku)"
      else:
        return f"{int(st_dani)} rad. dana (Kašnjenje)"

    df["Status_SLA"] = df.apply(provjeri_sla, axis=1)

  # Gornje Info trake
  total_posiljaka = len(df)
  st.markdown(
      f"📊 **Obrađeno pošiljaka: {total_posiljaka}** | Uspješno učitano"
  )
  st.markdown("---")

  # Definiranje tabova (kartica)
  tab1, tab2, tab3, tab4 = st.tabs([
      "📊 1. Pregled i Vizuali",
      "🚚 2. Tranzit i Rokovi",
      "💰 3. Usporedba Cijena",
      "📥 4. Preuzimanje Izvještaja",
  ])

  with tab1:
    st.subheader("Ključni pokazatelji i vizualna analitika")
    col1, col2, col3 = st.columns(3)

    total_neto = df["Iznos (bezPDV)"].sum()
    total_ugovor = df["Ugovorna_Cijena"].sum()
    total_razlika = df[df["Razlika_Preplaceno"] > 0]["Razlika_Preplaceno"].sum()

    col1.metric("Ukupno naplaćeno (bez PDV)", f"{total_neto:,.2f} EUR")
    col2.metric("Procjena po cjeniku", f"{total_ugovor:,.2f} EUR")
    col3.metric(
        "Uočeno preplaćeno", f"{total_razlika:,.2f} EUR", delta_color="inverse"
    )

    st.markdown("---")
    vc1, vc2 = st.columns(2)

    with vc1:
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

    with vc2:
      st.markdown("**Top 10 gradova po ukupnim troškovima**")
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
            color="Iznos (bezPDV)",
            labels={
                "Prim-mjesto": "Grad primatelj",
                "Iznos (bezPDV)": "Ukupno (EUR)",
            },
        )
        st.plotly_chart(fig2, use_container_width=True)

  with tab2:
    st.subheader("Analiza tranzita pošiljaka i provjera ugovornih rokova isporuke")
    if "Status_SLA" in df.columns:
      u_roku_cnt = len(
          df[df["Status_SLA"].astype(str).str.contains("U roku")]
      )
      postotak_u_roku = (
          (u_roku_cnt / total_posiljaka * 100) if total_posiljaka > 0 else 0
      )
      kasnjenje_cnt = len(
          df[df["Status_SLA"].astype(str).str.contains("Kašnjenje")]
      )

      sc1, sc2, sc3 = st.columns(3)
      sc1.metric(
          "Uredno isporučeno u roku",
          f"{postotak_u_roku:.1f}%",
          f"↑ {u_roku_cnt} pošiljaka",
      )
      sc2.metric(
          "Izvan ugovornog roka (Kašnjenje)",
          f"{kasnjenje_cnt}",
          delta_color="inverse",
      )
      sc3.metric("Ukupno analizirano pošiljaka s datumima", f"{total_posiljaka}")

    st.markdown("---")
    prikaz_tranzit = [
        "Br.rač.",
        "Usluga-naziv",
        "Prim-mjesto",
        "Prim.-pošt.br.",
        "Zona",
        "Odlazak",
        "Dostava",
        "Radni_Dani_Isporuke",
        "Status_SLA",
    ]
    st.dataframe(
        df[[c for c in prikaz_tranzit if c in df.columns]],
        use_container_width=True,
    )

  with tab3:
    st.subheader("Usporedba naplaćenih i ugovornih cijena (Revizija)")
    prikaz_cijene = [
        "Br.rač.",
        "Dat.rač.",
        "Usluga-naziv",
        "Prim-mjesto",
        "Vred.osn./količ.",
        "JM",
        "Iznos (bezPDV)",
        "Ugovorna_Cijena",
        "Razlika_Preplaceno",
    ]
    st.dataframe(
        df[[c for c in prikaz_cijene if c in df.columns]],
        use_container_width=True,
    )

  with tab4:
    st.subheader("Preuzimanje cjelovitog izvještaja u Excel formatu")
    output = io.BytesIO()
    with pd.ExcelWriter(output, engine="openpyxl") as writer:
      df.to_excel(writer, index=False, sheet_name="Revizija_i_Rokovi")
    excel_data = output.getvalue()

    st.download_button(
        label="📥 Preuzmi izvještaj revizije (Excel)",
        data=excel_data,
        file_name="intereuropa_revizija_cijena_i_rokova.xlsx",
        mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
    )
