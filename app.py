import streamlit as st
import google.generativeai as genai
from PIL import Image

st.set_page_config(page_title="Samketan Marketing Studio", page_icon="📸")

st.title("Samketan AI: Marketing Factory 🚀")
st.caption("Upload a product photo ➔ Get ready-to-post social media campaigns")

# --- SIDEBAR: SETTINGS & UPLOAD ---
st.sidebar.header("⚙️ Settings")
if "GEMINI_API_KEY" in st.secrets:
    api_key = st.secrets["GEMINI_API_KEY"]
    st.sidebar.success("✅ API Key Loaded")
else:
    api_key = st.sidebar.text_input("Enter Gemini API Key", type="password")

st.sidebar.markdown("---")
st.sidebar.header("📸 Visual Input")
uploaded_file = st.sidebar.file_uploader("Upload Product/Warehouse Photo", type=["jpg", "jpeg", "png"])

image = None
if uploaded_file is not None:
    image = Image.open(uploaded_file)
    st.sidebar.image(image, caption="Product Preview", use_container_width=True)

# --- MAIN SCREEN ---
product_context = st.text_input("What are we selling?", placeholder="e.g., Premium Grade Toor Dal from Kalaburagi")
target_audience = st.selectbox("Who is the target audience?", ["B2B (Wholesalers, Supermarkets)", "B2C (Direct Consumers)", "Corporate (For Warehouse Space)"])

if st.button("Generate Marketing Campaign"):
    if not api_key:
        st.error("Please enter your API Key!")
    elif not image:
        st.warning("Please upload a product photo first!")
    else:
        with st.spinner("Creative Director is analyzing the image and writing copy..."):
            genai.configure(api_key=api_key)
            
            # Using the Flash model as it has excellent vision capabilities
            model = genai.GenerativeModel('gemini-1.5-flash')
            
            prompt = f"""
            You are an expert Social Media Manager and Creative Director.
            Analyze the attached image.
            
            Product Context: {product_context}
            Target Audience: {target_audience}
            
            Create a complete, ready-to-publish marketing campaign. Format your output strictly with these headings:
            
            ### 👔 LinkedIn Post (Professional)
            Write a B2B focused post highlighting supply chain, quality, or business value. Include relevant professional hashtags.
            
            ### 📸 Instagram & Facebook Post (Consumer)
            Write a catchy, highly engaging post with emojis and viral hashtags. Make it visually appealing in text form.
            
            ### 💬 WhatsApp Broadcast
            Write a short, direct message suitable for forwarding. Include a clear Call to Action (CTA).
            
            ### 🎨 Poster Design Instructions
            Give the graphic designer 3 bullet points on exactly what text to overlay on this image to make a highly converting poster.
            """
            
            try:
                # We pass BOTH the prompt text and the image to the AI
                response = model.generate_content([prompt, image])
                st.success("✅ Campaign Generated Successfully!")
                st.markdown(response.text)
            except Exception as e:
                st.error(f"Failed to generate campaign: {e}")
