import os
import json
import streamlit as st
import resend

# Streamlit-sivumuotoilu
st.set_page_config(page_title="Toimenpide 1.3 - Haastattelujärjestelmä", layout="wide")

st.title("🌲 Metsäsektorin ilmastosopeutuminen – Kysely & Haastattelu")
st.markdown("### Toimenpide 1.3: Tulevaisuustyöskentely metsäteollisuuden muutos- ja sopeutumistarpeista")
st.info("Vastauksesi kerätään turvallisesti raakadata-arkistoon ja lähetetään sähköpostiin.")

# Sähköpostin lähetysfunktio Resend-rajapinnan kautta (toimii myös Streamlit Cloudissa)
def send_email_report(subject, body, files_to_attach):
    try:
        api_key = st.secrets.get("RESEND_API_KEY")
        if not api_key:
            return False, "RESEND_API_KEY puuttuu Streamlit Cloudin Secrets-asetuksista."
        
        resend.api_key = api_key
        receiver_email = st.secrets.get("EMAIL_TO", "karkimetsat@gmail.com")

        # Valmistellaan liitetiedostot Resendille
        liitteet = []
        for file_path in files_to_attach:
            if os.path.exists(file_path):
                with open(file_path, "rb") as f:
                    liitteet.append({
                        "filename": os.path.basename(file_path),
                        "content": list(f.read())
                    })

        params = {
            "from": "Metsähaastattelu <onboarding@resend.dev>",
            "to": [receiver_email],
            "subject": subject,
            "html": f"<p>{body.replace(chr(10), '<br>')}</p>",
            "attachments": liitteet
        }

        resend.Emails.send(params)
        return True, "Sähköposti lähetetty onnistuneesti!"
    except Exception as e:
        return False, f"Lähetysvirhe: {str(e)}"

# 1. Roolin valinta
rooli = st.selectbox(
    "Valitse sidosryhmäsi / roolisi:",
    ["Valitse...", "Metsänomistaja", "Puunostaja", "Puuteollisuus"]
)

if rooli != "Valitse...":
    st.divider()
    st.subheader(f"Kysymykset roolille: {rooli}")

    kysymykset = [
        "1. Ilmastonmuutoksen uhat ja riskit:\nMitkä ilmastonmuutokseen liittyvät ilmiöt (esim. tuhot, roudattomus, kuivuus) näet suurimpana uhkana omassa toiminnassasi seuraavan 10–20 vuoden aikana?",
        "2. Puulajisuhteet ja metsänhoito:\nMiten suhtaudut kuusen osuuden vähentämiseen sekä lehtipuiden ja sekametsien lisäämiseen talousmetsissä?",
        "3. Varautuminen ja sopeutumiskeinot:\nMitä käytännön toimenpiteitä teillä on jo tehty tai pitäisi tehdä ilmastoriskeihin sopeutumiseksi?",
        "4. Hakkuumäärät ja maankäytön rajoitteet:\nMiten sovitat/sovittaisitte yhteen puuntuotannon sekä ilmastonielu-, vesistö- ja monimuotoisuustavoitteet?",
        "5. Sääntely ja ohjauskeinot:\nMiten näet EU:n ja kansallisen ympäristösääntelyn (esim. LULUCF, ennallistaminen) vaikuttavan alan tulevaisuuteen?",
        "6. Tulevaisuuden näkymät ja yhteistyö:\nMikä on mielestäsi suurin este tai pullonkaula ilmastonkestävän metsatalouden toteuttamisessa käytännössä?"
    ]

    # Kyselylomake
    with st.form(key="haastattelu_lomake"):
        vastaukset = {}

        for i, q in enumerate(kysymykset, 1):
            st.markdown(f"**{q}**")
            
            audio_input = st.audio_input(f"🎙️ Nauhoita vastaus suoraan mikrofonilla:", key=f"audio_{i}")
            
            txt_input = st.text_area(
                f"Kirjoita vastaus {i} (jos et nauhoita ääntä):", 
                key=f"txt_{i}", 
                height=120
            )
            
            vastaukset[f"Kysymys_{i}"] = {
                "kysymys": q,
                "teksti": txt_input,
                "aanite": audio_input
            }
            st.divider()

        submit_button = st.form_submit_button(label="Tallenna ja lähetä vastaukset")

    if submit_button:
        processed_responses = []
        sisaltaako_aitoja_vastauksia = False
        haastattelu_id = os.urandom(4).hex()
        os.makedirs("vastausarkisto", exist_ok=True)

        attached_files = []

        for key, item in vastaukset.items():
            raw_text = item["teksti"].strip()
            has_audio = False
            audio_filename = None
            
            if item["aanite"] is not None:
                audio_filename = f"vastausarkisto/{rooli}_{haastattelu_id}_{key}.wav"
                with open(audio_filename, "wb") as f:
                    f.write(item["aanite"].getbuffer())
                has_audio = True
                sisaltaako_aitoja_vastauksia = True
                attached_files.append(audio_filename)

            if raw_text and raw_text.lower() not in ["xxx", "x", "-", "."]:
                sisaltaako_aitoja_vastauksia = True
                lopullinen_vastaus = raw_text
            else:
                lopullinen_vastaus = "Ei tekstivastausta"

            processed_responses.append({
                "teema": item["kysymys"],
                "raaka_vastaus": lopullinen_vastaus,
                "aanite_tallennettu": has_audio,
                "aanite_tiedosto": os.path.basename(audio_filename) if has_audio else None
            })

        if not sisaltaako_aitoja_vastauksia:
            st.warning("⚠️ Lomakkeelle ei syötetty tekstiä eikä äänitteitä. Tallennusta ei tehty.")
        else:
            tiedostonimi_raaka = f"vastausarkisto/{rooli}_{haastattelu_id}_RAAKADATA.json"

            with open(tiedostonimi_raaka, "w", encoding="utf-8") as f:
                json.dump({"rooli": rooli, "vastaukset": processed_responses}, f, ensure_ascii=False, indent=2)
            
            attached_files.append(tiedostonimi_raaka)

            subject = f"Uusi haastatteluvastaus: {rooli} (ID: {haastattelu_id})"
            body = f"Hei!\n\nUusi haastatteluvastaus saapui järjestelmään.\nRooli: {rooli}\nID: {haastattelu_id}\n\nLiitteenä ovat JSON-raakadata sekä mahdolliset äänitiedostot."

            with st.spinner("Lähetetään haastatteludataa sähköpostiin..."):
                email_success, email_msg = send_email_report(subject, body, attached_files)

            if email_success:
                st.success("Vastaukset tallennettu ja lähetetty onnistuneesti sähköpostiin!")
                st.info(f"Tallennetut tiedostot löytyvät kansiosta: `vastausarkisto/` (tiedosto: `{tiedostonimi_raaka}`)")
            else:
                st.warning(f"Vastaukset tallennettiin paikallisesti, mutta sähköpostin lähetyksessä oli ongelma: {email_msg}")
