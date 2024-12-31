import streamlit as st

def main():
    st.title("Minimal Test App")
    st.write("This is a test of the Streamlit server.")
    
    if st.button("Click me"):
        st.write("Button clicked!")

if __name__ == "__main__":
    main()
