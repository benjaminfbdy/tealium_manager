import streamlit as st
import json
from controllers.server_side_controller import parse_server_side_export

def render_server_side_inventory_view():
    st.header("🔬 Inventaire Server-Side (EventStream/AudienceStream)")
    st.info("Cette fonctionnalité (en R&D) analyse un fichier d'export JSON de votre profil Tealium Server-Side.")

    uploaded_file = st.file_uploader(
        "Chargez votre fichier d'export JSON",
        type=['json']
    )

    if uploaded_file is not None:
        try:
            # To convert to a string based IO:
            string_data = uploaded_file.getvalue().decode("utf-8")
            data = json.loads(string_data)
            
            with st.spinner("Analyse du fichier JSON..."):
                parsed_data = parse_server_side_export(data)

            if parsed_data.get("error"):
                st.error(parsed_data["error"])
            else:
                st.success("Analyse terminée !")
                
                # --- Summary Metrics ---
                summ = parsed_data["summary"]
                c1, c2, c3, c4 = st.columns(4)
                c1.metric("Connecteurs", summ.get("connectors", 0))
                c2.metric("Audiences", summ.get("audiences", 0))
                c3.metric("Attr. Visiteur", summ.get("visitor_attributes", 0))
                c4.metric("Attr. Visite", summ.get("visit_attributes", 0))
                
                st.divider()

                # --- Tabs Layout ---
                tab_connectors, tab_visitor, tab_visit = st.tabs([
                    "🔌 Connecteurs & Mappings", 
                    "👤 Attributs Visiteur", 
                    "📅 Attributs Visite"
                ])

                with tab_connectors:
                    df_conn = parsed_data["connectors"]
                    if not df_conn.empty:
                        st.caption("Liste détaillée des mappings par connecteur et action.")
                        
                        # Filter by Connector
                        connectors_list = df_conn["Connecteur"].unique()
                        selected_conn = st.selectbox("Filtrer par Connecteur", ["Tous"] + list(connectors_list))
                        
                        if selected_conn != "Tous":
                            df_display = df_conn[df_conn["Connecteur"] == selected_conn]
                        else:
                            df_display = df_conn
                        
                        st.dataframe(df_display, use_container_width=True, hide_index=True)
                    else:
                        st.info("Aucun connecteur trouvé.")

                with tab_visitor:
                    st.dataframe(parsed_data["visitor_attributes"], use_container_width=True, hide_index=True)

                with tab_visit:
                    st.dataframe(parsed_data["visit_attributes"], use_container_width=True, hide_index=True)

        except json.JSONDecodeError:
            st.error("Erreur : Le fichier fourni n'est pas un JSON valide.")
        except Exception as e:
            st.error(f"Une erreur inattendue est survenue : {e}")