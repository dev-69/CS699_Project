from youtube_search import YoutubeSearch
from ddgs import DDGS
import random

IMG_MIT = "https://upload.wikimedia.org/wikipedia/commons/thumb/0/01/MIT_OpenCourseWare_logo.svg/1200px-MIT_OpenCourseWare_logo.svg.png"
IMG_COURSERA = "https://upload.wikimedia.org/wikipedia/commons/thumb/9/97/Coursera-Logo_600x600.svg/1200px-Coursera-Logo_600x600.svg.png"
IMG_UDEMY = "https://www.udemy.com/staticx/udemy/images/v7/logo-udemy.svg"

def get_youtube_videos(topic, limit=3):
    """ Tier 1: Free Video Tutorials """
    try:
        results = YoutubeSearch(f"{topic} full course tutorial", max_results=limit).to_dict()
        videos = []
        for vid in results:
            videos.append({
                "title": vid['title'],
                "link": f"https://www.youtube.com/watch?v={vid['id']}",
                "thumbnail": vid['thumbnails'][0],
                "source": "YouTube",
                "type": "Free Video"
            })
        return videos
    except: return []

def get_university_lectures(topic, limit=2):
    """ Tier 2: Top University Lectures (MIT, Stanford, Harvard) """
    lectures = []
    query = f"site:ocw.mit.edu OR site:online.stanford.edu OR site:edx.org {topic} lecture"
    
    try:
        with DDGS() as ddgs:
            results = list(ddgs.text(query, max_results=limit))
            for res in results:
                lectures.append({
                    "title": res['title'],
                    "link": res['href'],
                    "thumbnail": IMG_MIT, 
                    "source": "University",
                    "type": "Lecture / Academic"
                })
    except Exception as e:
        print(f"Uni Search Error: {e}")

 
    if not lectures:
        lectures.append({
            "title": f"Browse '{topic}' on MIT OCW",
            "link": f"https://ocw.mit.edu/search/?q={topic}",
            "thumbnail": IMG_MIT,
            "source": "MIT OCW",
            "type": "Direct Search"
        })
        
    return lectures

def get_paid_courses(topic, limit=2):
    """ Tier 3: Paid Certifications (Udemy, Coursera) """
    courses = []
    query = f"site:udemy.com OR site:coursera.org {topic} course"
    
    try:
        with DDGS() as ddgs:
            results = list(ddgs.text(query, max_results=limit))
            for res in results:
                img = IMG_COURSERA
                if "udemy" in res['href']: img = IMG_UDEMY
                
                courses.append({
                    "title": res['title'],
                    "link": res['href'],
                    "thumbnail": img,
                    "source": "Coursera/Udemy",
                    "type": "Paid Certificate"
                })
    except Exception as e:
        print(f"Paid Search Error: {e}")


    if not courses:
        courses.append({
            "title": f"Find '{topic}' Courses on Coursera",
            "link": f"https://www.coursera.org/search?query={topic}",
            "thumbnail": IMG_COURSERA,
            "source": "Coursera",
            "type": "Direct Search"
        })

    return courses

def get_recommendations(topic):
    """ Master function returning a dict of 3 categories """
    return {
        "free": get_youtube_videos(topic),
        "university": get_university_lectures(topic),
        "paid": get_paid_courses(topic)
    }