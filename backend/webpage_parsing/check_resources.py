from .episode_summaries import parse_resources  
from bs4 import BeautifulSoup 


path = "C:/Users/Pinda/Proyectos/BioHackAgent/backend/output/episode_1303.html"

with open(path, "r", encoding="utf-8") as file:
    html_content = file.read()

soup = BeautifulSoup(html_content, "html.parser")

resources = parse_resources(soup)

print(resources)
