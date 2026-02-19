import streamlit as st
from views.component_renderers import setup_page

# --- Page Configuration ---
setup_page()

# --- Main Page Content ---
st.title("👋 Bienvenue sur le Tealium Manager !")

st.markdown("""
Cet outil a été conçu pour simplifier et optimiser la gestion de vos configurations Tealium iQ et de vos rapports Adobe Analytics.

---

### 🚀 Navigation

Utilisez la barre latérale pour naviguer entre les différentes sections :

- 📄 **Pages Principales** : Accédez à l'inventaire Tealium, à l'historique des MEP ou au Requeteur Adobe.
- ⚙️ **Configuration** : Visualisez et activez vos configurations Tealium et Adobe. Celles-ci sont maintenant gérées directement dans votre fichier `.streamlit/secrets.toml`.
- 🔩 **Administration** : Consultez l'état de la base de données de cache et effectuez des opérations de maintenance.

### 💡 Premiers Pas

1.  Assurez-vous que votre fichier `.streamlit/secrets.toml` est correctement rempli.
2.  Allez dans les pages de **Configuration Tealium** et **Configuration Adobe** pour activer les profils avec lesquels vous souhaitez travailler.
3.  Explorez les fonctionnalités !
""")



