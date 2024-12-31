import streamlit as st

def main():
    st.title("Minimal OSM Viewer")
    st.write("If you can see this, the application is working!")
    
    if st.button("Click me"):
        st.write("The application is responding to user input!")

if __name__ == "__main__":
    main()
