"""Raw data and export tab."""

import streamlit as st
import pandas as pd

def render(df):
    st.markdown("### Raw Round Data")
    
    st.dataframe(
        df.sort_values("Date", ascending=False),
        use_container_width=True,
        hide_index=True
    )
    
    @st.cache_data
    def convert_df(df):
        return df.to_csv(index=False).encode('utf-8')
        
    csv = convert_df(df)
    
    st.download_button(
        label="📥 Download as CSV",
        data=csv,
        file_name="geoguessr_duels_export.csv",
        mime="text/csv",
    )
