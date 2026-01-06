import streamlit as st
from typing import Dict, List, Any

def render_comparison(comparison_data: Dict[str, Any]):
    """
    Renders the comparison results between two revisions.
    """
    rev1_id = comparison_data.get("rev1_id", "N/A")
    rev2_id = comparison_data.get("rev2_id", "N/A")
    diff = comparison_data.get("diff", {})
    uid_map = comparison_data.get("uid_map", {})

    st.header(f"Comparaison entre MEP `{rev1_id}` et `{rev2_id}`")

    if not diff:
        st.info("Aucune différence détectée entre ces deux versions.")
        return

    component_map = {
        "Variables": "variables",
        "Tags": "tags",
        "Load Rules": "loadRules",
        "Extensions": "extensions",
        "Events": "events"
    }

    for display_name, key in component_map.items():
        component_diff = diff.get(key, {})
        added = component_diff.get("added", [])
        removed = component_diff.get("removed", [])
        modified = component_diff.get("modified", [])

        if not added and not removed and not modified:
            continue

        with st.expander(f"**{display_name}** - Ajouts: {len(added)}, Suppressions: {len(removed)}, Modifications: {len(modified)}"):
            
            if added:
                st.subheader("✅ Ajouté")
                for item in added:
                    st.text(item.get('name', item.get('alias', 'N/A')))
            
            if removed:
                st.subheader("❌ Supprimé")
                for item in removed:
                    st.text(item.get('name', item.get('alias', 'N/A')))

            if modified:
                st.subheader("🔄 Modifié")
                for item in modified:
                    st.text(f"Avant : {item['before'].get('name', item['before'].get('alias', 'N/A'))}")
                    st.text(f"Après : {item['after'].get('name', item['after'].get('alias', 'N/A'))}")
                    # A more detailed diff view will be added here later
                    st.code(f"Avant: {item['before']}\nAprès: {item['after']}", language="diff")

            st.markdown("---")
