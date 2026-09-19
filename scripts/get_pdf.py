import gdown
import re

pdfs = gdown.download_folder(
    id="1wUxTh8sIJ6iN9F4a0sU4AeKgq5hT4WVB",
    output="assets/pdf",
    quiet=True,
    use_cookies=False,
)


for pdf in pdfs:
    year = re.search(r"\d{4}", str(pdf)).group()
    with open(f"content/blog/beszamolo{year}.md", "w") as md:
        md.write(f"""---\ntitle: "{year}"\ndate: {year}-01-01\nfeatureImage: images/allpost/beszamolocover{year}.png\npostImage: images/single-blog/beszamolocover.png\npdf: {pdf.replace("assets/", "")}\n---\n""")