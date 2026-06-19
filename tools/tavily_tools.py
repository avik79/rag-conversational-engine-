"""Tavily API tools for IRIS agent"""
import os
from typing import Any
from tavily import TavilyClient


def fetch_tavily_weather(locations: list[str]) -> dict[str, Any]:
    """Fetch weather data from Tavily API for given locations"""
    try:
        api_key = os.getenv("TAVILY_API_KEY")
        if not api_key:
            raise ValueError("TAVILY_API_KEY not set in environment")

        client = TavilyClient(api_key=api_key)

        all_results = []
        for location in locations:
            query = f"weather in {location}"
            response = client.search(query=query, max_results=3)

            for result in response.get("results", []):
                all_results.append({
                    "location": location,
                    "title": result.get("title"),
                    "content": result.get("content"),
                    "source": result.get("source"),
                    "url": result.get("url"),
                    "type": "weather",
                })

        return {
            "success": True,
            "results": all_results,
            "count": len(all_results),
        }
    except Exception as e:
        return {
            "success": False,
            "error": str(e),
            "results": [],
            "count": 0,
        }


def fetch_tavily_news(topics: list[str]) -> dict[str, Any]:
    """Fetch news data from Tavily API for given topics"""
    try:
        api_key = os.getenv("TAVILY_API_KEY")
        if not api_key:
            raise ValueError("TAVILY_API_KEY not set in environment")

        client = TavilyClient(api_key=api_key)

        all_results = []
        for topic in topics:
            response = client.search(query=topic, max_results=3)

            for result in response.get("results", []):
                all_results.append({
                    "topic": topic,
                    "title": result.get("title"),
                    "content": result.get("content"),
                    "source": result.get("source"),
                    "url": result.get("url"),
                    "type": "news",
                })

        return {
            "success": True,
            "results": all_results,
            "count": len(all_results),
        }
    except Exception as e:
        return {
            "success": False,
            "error": str(e),
            "results": [],
            "count": 0,
        }
