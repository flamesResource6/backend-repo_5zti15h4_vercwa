import os
from typing import Literal, Dict, Any
from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel, Field
from urllib.parse import quote_plus

app = FastAPI()

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


class GenerateRequest(BaseModel):
    idea: str = Field(..., min_length=3, description="Core content idea")
    tone: Literal["professional", "witty", "urgent"] = "professional"


class PlatformPost(BaseModel):
    text: str
    image_url: str
    width: int
    height: int
    platform: Literal["linkedin", "twitter", "instagram"]


class GenerateResponse(BaseModel):
    linkedin: PlatformPost
    twitter: PlatformPost
    instagram: PlatformPost


@app.get("/")
def read_root():
    return {"message": "Hello from FastAPI Backend!"}


@app.get("/api/hello")
def hello():
    return {"message": "Hello from the backend API!"}


@app.get("/test")
def test_database():
    """Test endpoint to check if database is available and accessible"""
    response = {
        "backend": "✅ Running",
        "database": "❌ Not Available",
        "database_url": None,
        "database_name": None,
        "connection_status": "Not Connected",
        "collections": []
    }
    
    try:
        # Try to import database module
        from database import db
        
        if db is not None:
            response["database"] = "✅ Available"
            response["database_url"] = "✅ Configured"
            response["database_name"] = db.name if hasattr(db, 'name') else "✅ Connected"
            response["connection_status"] = "Connected"
            
            # Try to list collections to verify connectivity
            try:
                collections = db.list_collection_names()
                response["collections"] = collections[:10]  # Show first 10 collections
                response["database"] = "✅ Connected & Working"
            except Exception as e:
                response["database"] = f"⚠️  Connected but Error: {str(e)[:50]}"
        else:
            response["database"] = "⚠️  Available but not initialized"
            
    except ImportError:
        response["database"] = "❌ Database module not found (run enable-database first)"
    except Exception as e:
        response["database"] = f"❌ Error: {str(e)[:50]}"
    
    # Check environment variables
    import os
    response["database_url"] = "✅ Set" if os.getenv("DATABASE_URL") else "❌ Not Set"
    response["database_name"] = "✅ Set" if os.getenv("DATABASE_NAME") else "❌ Not Set"
    
    return response


# -------- Content Generation Utilities (now with AI image URLs) -------- #

def _apply_tone(prefix: str, tone: str) -> str:
    tone_map: Dict[str, str] = {
        "professional": f"{prefix} Let's focus on measurable value, clear outcomes, and next steps.",
        "witty": f"{prefix} Let's keep it sharp, playful, and scroll-stopping.",
        "urgent": f"{prefix} Act now—this window won't stay open long.",
    }
    return tone_map.get(tone, prefix)


def _hashtagify(keywords: list[str]) -> str:
    tags = [f"#{k.strip().replace(' ', '')[:22]}" for k in keywords if k.strip()]
    # limit hashtags for platform norms
    return " ".join(tags[:12])


def _keywords_from_idea(idea: str) -> list[str]:
    parts = [p.strip().lower() for p in idea.replace("-", " ").replace("/", " ").split()]
    uniq = []
    for p in parts:
        if p.isalpha() and p not in uniq:
            uniq.append(p)
    # ensure some generic tags exist
    if not uniq:
        uniq = ["creator", "content", "marketing"]
    return uniq[:10]


def _ai_image(width: int, height: int, prompt: str) -> str:
    """
    Generate an image URL via Pollinations AI (no API key required).
    This returns a hosted image generated from the prompt at the specified size.
    """
    qp = quote_plus(prompt[:300])
    return (
        f"https://image.pollinations.ai/prompt/{qp}?width={width}&height={height}&nologo=true"
    )


def generate_posts(idea: str, tone: str) -> Dict[str, PlatformPost]:
    idea_clean = idea.strip()
    if len(idea_clean) < 3:
        raise ValueError("Idea must be at least 3 characters long")

    keywords = _keywords_from_idea(idea_clean)
    tone_intro = {
        "professional": "Here's a strategic take:",
        "witty": "Hot take (with a wink):",
        "urgent": "Don't sleep on this:",
    }[tone]

    # Shared style cues for imagery
    visual_style = {
        "professional": "clean minimalist corporate, bold typography, soft gradients, high contrast",
        "witty": "playful vibrant, 3D icons, colorful gradients, dynamic composition, stickers",
        "urgent": "bold red accents, high contrast, motion blur, impactful headline graphic",
    }[tone]

    # LinkedIn (long-form)
    li_width, li_height = 1200, 627  # 1.91:1
    li_paragraphs = [
        f"{tone_intro} {idea_clean}.",
        _apply_tone("Why it matters:", tone),
        "• Impact: Drive results through clarity and focus.\n"
        "• Approach: Start small, iterate fast, and measure what matters.\n"
        "• Outcome: Momentum that compounds.",
        "Curious to dive deeper? Let's connect.",
    ]
    li_text = "\n\n".join(li_paragraphs)
    li_prompt = (
        f"LinkedIn banner, {visual_style}, topic: {idea_clean}, icons for {', '.join(keywords)}, "
        f"branding-friendly, vector style, centered composition"
    )
    li_img = _ai_image(li_width, li_height, li_prompt)

    # Twitter/X (short & punchy)
    tw_width, tw_height = 1200, 675  # 16:9
    punchy = f"{idea_clean} → Make it real. {('' if tone!='witty' else '😉 ')}#buildinpublic"
    tw_text = punchy[:275]
    tw_prompt = (
        f"Twitter/X social card, {visual_style}, topic: {idea_clean}, high readability, "
        f"strong focal point, modern UI motif"
    )
    tw_img = _ai_image(tw_width, tw_height, tw_prompt)

    # Instagram (visual + hashtags)
    ig_width, ig_height = 1080, 1350  # 4:5 portrait
    ig_caption_core = _apply_tone(idea_clean, tone)
    ig_tags = _hashtagify([*keywords, tone, "socialmedia", "content", "brand"])
    ig_text = f"{ig_caption_core}\n\n{ig_tags}"
    ig_prompt = (
        f"Instagram portrait poster, {visual_style}, topic: {idea_clean}, editorial design, "
        f"eye-catching, aesthetic photography + graphic overlay"
    )
    ig_img = _ai_image(ig_width, ig_height, ig_prompt)

    return {
        "linkedin": PlatformPost(text=li_text, image_url=li_img, width=li_width, height=li_height, platform="linkedin"),
        "twitter": PlatformPost(text=tw_text, image_url=tw_img, width=tw_width, height=tw_height, platform="twitter"),
        "instagram": PlatformPost(text=ig_text, image_url=ig_img, width=ig_width, height=ig_height, platform="instagram"),
    }


@app.post("/api/generate", response_model=GenerateResponse)
def generate(req: GenerateRequest):
    try:
        posts = generate_posts(req.idea, req.tone)
        return GenerateResponse(**posts)  # type: ignore
    except ValueError as ve:
        raise HTTPException(status_code=400, detail=str(ve))
    except Exception as e:
        raise HTTPException(status_code=500, detail="Failed to generate content")


if __name__ == "__main__":
    import uvicorn
    port = int(os.getenv("PORT", 8000))
    uvicorn.run(app, host="0.0.0.0", port=port)
