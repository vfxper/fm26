"""
Tests for Player Search API endpoints
"""

import pytest
from httpx import AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.player import Player


@pytest.fixture
async def sample_players(test_db_session: AsyncSession):
    """
    Create sample players for testing
    """
    players = [
        Player(
            uid="TEST001",
            name="Lionel Messi",
            position="AM/ST RL",
            age=36,
            nationality="Argentina",
            club="Inter Miami",
            ca=180,
            pa=200,
            corners=18,
            crossing=17,
            dribbling=20,
            finishing=19,
            first_touch=20,
            free_kicks=19,
            heading=10,
            long_shots=18,
            long_throws=8,
            marking=8,
            passing=19,
            penalty=18,
            tackling=7,
            technique=20,
            aggression=12,
            anticipation=19,
            bravery=14,
            composure=20,
            concentration=18,
            decisions=19,
            determination=18,
            flair=20,
            leadership=16,
            off_the_ball=19,
            positioning=18,
            teamwork=17,
            vision=20,
            work_rate=15,
            acceleration=16,
            agility=18,
            balance=19,
            jumping=10,
            stamina=15,
            pace=16,
            endurance=16,
            strength=11,
            price="50M",
            wage=500000,
            height=170,
            weight=67,
            left_foot=20,
            right_foot=12,
            traits="Dribbles Often, Finesse Shot, Playmaker"
        ),
        Player(
            uid="TEST002",
            name="Cristiano Ronaldo",
            position="ST",
            age=38,
            nationality="Portugal",
            club="Al Nassr",
            ca=175,
            pa=200,
            corners=15,
            crossing=14,
            dribbling=17,
            finishing=20,
            first_touch=18,
            free_kicks=18,
            heading=19,
            long_shots=19,
            long_throws=10,
            marking=7,
            passing=16,
            penalty=19,
            tackling=6,
            technique=18,
            aggression=14,
            anticipation=19,
            bravery=18,
            composure=19,
            concentration=17,
            decisions=18,
            determination=20,
            flair=18,
            leadership=19,
            off_the_ball=20,
            positioning=19,
            teamwork=15,
            vision=17,
            work_rate=18,
            acceleration=17,
            agility=16,
            balance=17,
            jumping=19,
            stamina=18,
            pace=17,
            endurance=19,
            strength=18,
            price="45M",
            wage=450000,
            height=187,
            weight=84,
            left_foot=12,
            right_foot=20,
            traits="Power Header, Long Shot Taker"
        ),
        Player(
            uid="TEST003",
            name="Erling Haaland",
            position="ST",
            age=23,
            nationality="Norway",
            club="Manchester City",
            ca=185,
            pa=195,
            corners=8,
            crossing=10,
            dribbling=14,
            finishing=20,
            first_touch=16,
            free_kicks=10,
            heading=17,
            long_shots=16,
            long_throws=12,
            marking=6,
            passing=13,
            penalty=17,
            tackling=5,
            technique=15,
            aggression=15,
            anticipation=19,
            bravery=16,
            composure=18,
            concentration=16,
            decisions=17,
            determination=19,
            flair=14,
            leadership=12,
            off_the_ball=20,
            positioning=19,
            teamwork=16,
            vision=14,
            work_rate=17,
            acceleration=19,
            agility=16,
            balance=15,
            jumping=18,
            stamina=18,
            pace=19,
            endurance=18,
            strength=19,
            price="150M",
            wage=400000,
            height=194,
            weight=88,
            left_foot=18,
            right_foot=12,
            traits="Clinical Finisher, Speed Demon"
        ),
        Player(
            uid="TEST004",
            name="Kylian Mbappe",
            position="AM/ST RL",
            age=25,
            nationality="France",
            club="Paris Saint-Germain",
            ca=190,
            pa=200,
            corners=12,
            crossing=15,
            dribbling=19,
            finishing=19,
            first_touch=19,
            free_kicks=14,
            heading=13,
            long_shots=17,
            long_throws=10,
            marking=7,
            passing=17,
            penalty=16,
            tackling=6,
            technique=19,
            aggression=13,
            anticipation=19,
            bravery=15,
            composure=18,
            concentration=17,
            decisions=18,
            determination=18,
            flair=19,
            leadership=14,
            off_the_ball=20,
            positioning=19,
            teamwork=16,
            vision=18,
            work_rate=17,
            acceleration=20,
            agility=19,
            balance=18,
            jumping=15,
            stamina=18,
            pace=20,
            endurance=18,
            strength=15,
            price="180M",
            wage=600000,
            height=178,
            weight=73,
            left_foot=12,
            right_foot=20,
            traits="Speed Demon, Clinical Finisher"
        ),
        Player(
            uid="TEST005",
            name="Pedri",
            position="MC",
            age=21,
            nationality="Spain",
            club="Barcelona",
            ca=165,
            pa=185,
            corners=14,
            crossing=13,
            dribbling=17,
            finishing=12,
            first_touch=18,
            free_kicks=13,
            heading=8,
            long_shots=14,
            long_throws=8,
            marking=11,
            passing=18,
            penalty=13,
            tackling=12,
            technique=18,
            aggression=9,
            anticipation=17,
            bravery=13,
            composure=17,
            concentration=16,
            decisions=17,
            determination=16,
            flair=16,
            leadership=12,
            off_the_ball=15,
            positioning=16,
            teamwork=18,
            vision=18,
            work_rate=16,
            acceleration=15,
            agility=17,
            balance=17,
            jumping=10,
            stamina=16,
            pace=15,
            endurance=16,
            strength=10,
            price="80M",
            wage=150000,
            height=174,
            weight=60,
            left_foot=18,
            right_foot=10,
            traits="Playmaker, Technical"
        )
    ]
    
    for player in players:
        test_db_session.add(player)
    
    await test_db_session.commit()
    
    return players


@pytest.mark.asyncio
class TestPlayerSearchAPI:
    """Test suite for player search API endpoints"""
    
    async def test_search_players_post_no_filters(self, client: AsyncClient, sample_players):
        """Test POST /api/players/search with no filters returns all players"""
        response = await client.post("/api/players/search", json={})
        
        assert response.status_code == 200
        data = response.json()
        
        assert "players" in data
        assert "total" in data
        assert "limit" in data
        assert "offset" in data
        assert "has_more" in data
        
        assert data["total"] == 5
        assert len(data["players"]) == 5
        assert data["limit"] == 50
        assert data["offset"] == 0
        assert data["has_more"] is False
    
    async def test_search_players_post_with_text_search(self, client: AsyncClient, sample_players):
        """Test POST /api/players/search with text search"""
        response = await client.post("/api/players/search", json={
            "search_text": "Messi",
            "order_by": "relevance"
        })
        
        assert response.status_code == 200
        data = response.json()
        
        assert data["total"] == 1
        assert len(data["players"]) == 1
        assert data["players"][0]["name"] == "Lionel Messi"
    
    async def test_search_players_post_with_position_filter(self, client: AsyncClient, sample_players):
        """Test POST /api/players/search with position filter"""
        response = await client.post("/api/players/search", json={
            "position": "ST",
            "order_by": "ca"
        })
        
        assert response.status_code == 200
        data = response.json()
        
        # Should match players with "ST" in their position
        assert data["total"] >= 3  # Messi (AM/ST RL), Ronaldo (ST), Haaland (ST), Mbappe (AM/ST RL)
        
        # Check that results are sorted by CA descending
        cas = [p["ca"] for p in data["players"]]
        assert cas == sorted(cas, reverse=True)
    
    async def test_search_players_post_with_age_filter(self, client: AsyncClient, sample_players):
        """Test POST /api/players/search with age filter"""
        response = await client.post("/api/players/search", json={
            "min_age": 20,
            "max_age": 25,
            "order_by": "age"
        })
        
        assert response.status_code == 200
        data = response.json()
        
        assert data["total"] == 3  # Pedri (21), Haaland (23), Mbappe (25)
        
        # Check that all players are within age range
        for player in data["players"]:
            assert 20 <= player["age"] <= 25
        
        # Check that results are sorted by age ascending
        ages = [p["age"] for p in data["players"]]
        assert ages == sorted(ages)
    
    async def test_search_players_post_with_ca_filter(self, client: AsyncClient, sample_players):
        """Test POST /api/players/search with CA filter"""
        response = await client.post("/api/players/search", json={
            "min_ca": 180,
            "order_by": "ca"
        })
        
        assert response.status_code == 200
        data = response.json()
        
        assert data["total"] == 3  # Messi (180), Haaland (185), Mbappe (190)
        
        # Check that all players have CA >= 180
        for player in data["players"]:
            assert player["ca"] >= 180
    
    async def test_search_players_post_with_nationality_filter(self, client: AsyncClient, sample_players):
        """Test POST /api/players/search with nationality filter"""
        response = await client.post("/api/players/search", json={
            "nationality": "Argentina",
            "order_by": "name"
        })
        
        assert response.status_code == 200
        data = response.json()
        
        assert data["total"] == 1
        assert data["players"][0]["name"] == "Lionel Messi"
        assert data["players"][0]["nationality"] == "Argentina"
    
    async def test_search_players_post_with_club_filter(self, client: AsyncClient, sample_players):
        """Test POST /api/players/search with club filter"""
        response = await client.post("/api/players/search", json={
            "club": "Barcelona",
            "order_by": "name"
        })
        
        assert response.status_code == 200
        data = response.json()
        
        assert data["total"] == 1
        assert data["players"][0]["name"] == "Pedri"
        assert data["players"][0]["club"] == "Barcelona"
    
    async def test_search_players_post_with_pagination(self, client: AsyncClient, sample_players):
        """Test POST /api/players/search with pagination"""
        # First page
        response = await client.post("/api/players/search", json={
            "limit": 2,
            "offset": 0,
            "order_by": "name"
        })
        
        assert response.status_code == 200
        data = response.json()
        
        assert data["total"] == 5
        assert len(data["players"]) == 2
        assert data["limit"] == 2
        assert data["offset"] == 0
        assert data["has_more"] is True
        
        # Second page
        response = await client.post("/api/players/search", json={
            "limit": 2,
            "offset": 2,
            "order_by": "name"
        })
        
        assert response.status_code == 200
        data = response.json()
        
        assert data["total"] == 5
        assert len(data["players"]) == 2
        assert data["limit"] == 2
        assert data["offset"] == 2
        assert data["has_more"] is True
        
        # Last page
        response = await client.post("/api/players/search", json={
            "limit": 2,
            "offset": 4,
            "order_by": "name"
        })
        
        assert response.status_code == 200
        data = response.json()
        
        assert data["total"] == 5
        assert len(data["players"]) == 1
        assert data["limit"] == 2
        assert data["offset"] == 4
        assert data["has_more"] is False
    
    async def test_search_players_post_with_multiple_filters(self, client: AsyncClient, sample_players):
        """Test POST /api/players/search with multiple filters combined"""
        response = await client.post("/api/players/search", json={
            "position": "ST",
            "min_age": 20,
            "max_age": 30,
            "min_ca": 180,
            "order_by": "ca"
        })
        
        assert response.status_code == 200
        data = response.json()
        
        # Should match Haaland (23, ST, 185) and Mbappe (25, AM/ST RL, 190)
        assert data["total"] >= 2
        
        # Check that all players match all filters
        for player in data["players"]:
            assert "ST" in player["position"]
            assert 20 <= player["age"] <= 30
            assert player["ca"] >= 180
    
    async def test_search_players_post_invalid_age_range(self, client: AsyncClient, sample_players):
        """Test POST /api/players/search with invalid age range"""
        response = await client.post("/api/players/search", json={
            "min_age": 30,
            "max_age": 20
        })
        
        assert response.status_code == 400
        data = response.json()
        assert "error" in data
    
    async def test_search_players_post_invalid_ca_range(self, client: AsyncClient, sample_players):
        """Test POST /api/players/search with invalid CA range"""
        response = await client.post("/api/players/search", json={
            "min_ca": 200,
            "max_ca": 100
        })
        
        assert response.status_code == 400
        data = response.json()
        assert "error" in data
    
    async def test_search_players_post_invalid_order_by(self, client: AsyncClient, sample_players):
        """Test POST /api/players/search with invalid order_by"""
        response = await client.post("/api/players/search", json={
            "order_by": "invalid"
        })
        
        assert response.status_code == 422
        data = response.json()
        assert "error" in data
    
    async def test_search_players_post_relevance_without_search_text(self, client: AsyncClient, sample_players):
        """Test POST /api/players/search with relevance order but no search_text"""
        response = await client.post("/api/players/search", json={
            "order_by": "relevance"
        })
        
        assert response.status_code == 400
        data = response.json()
        assert "error" in data
    
    async def test_search_players_get_no_filters(self, client: AsyncClient, sample_players):
        """Test GET /api/players/search with no filters"""
        response = await client.get("/api/players/search")
        
        assert response.status_code == 200
        data = response.json()
        
        assert data["total"] == 5
        assert len(data["players"]) == 5
    
    async def test_search_players_get_with_query_params(self, client: AsyncClient, sample_players):
        """Test GET /api/players/search with query parameters"""
        response = await client.get(
            "/api/players/search",
            params={
                "position": "ST",
                "min_ca": 180,
                "order_by": "ca",
                "limit": 10
            }
        )
        
        assert response.status_code == 200
        data = response.json()
        
        assert data["total"] >= 2
        
        # Check that all players match filters
        for player in data["players"]:
            assert "ST" in player["position"]
            assert player["ca"] >= 180
    
    async def test_get_filter_options(self, client: AsyncClient, sample_players):
        """Test GET /api/players/filter-options"""
        response = await client.get("/api/players/filter-options")
        
        assert response.status_code == 200
        data = response.json()
        
        assert "positions" in data
        assert "nationalities" in data
        assert "clubs" in data
        assert "age_range" in data
        assert "ca_range" in data
        assert "pa_range" in data
        
        # Check that positions include expected values
        assert "ST" in data["positions"]
        assert "MC" in data["positions"]
        
        # Check that nationalities include expected values
        assert "Argentina" in data["nationalities"]
        assert "France" in data["nationalities"]
        
        # Check that clubs include expected values
        assert "Barcelona" in data["clubs"]
        assert "Manchester City" in data["clubs"]
        
        # Check age range
        assert data["age_range"]["min"] == 21
        assert data["age_range"]["max"] == 38
        
        # Check CA range
        assert data["ca_range"]["min"] == 165
        assert data["ca_range"]["max"] == 190
        
        # Check PA range
        assert data["pa_range"]["min"] == 185
        assert data["pa_range"]["max"] == 200
    
    async def test_player_response_contains_all_attributes(self, client: AsyncClient, sample_players):
        """Test that player response contains all required attributes"""
        response = await client.post("/api/players/search", json={
            "search_text": "Messi",
            "order_by": "relevance"
        })
        
        assert response.status_code == 200
        data = response.json()
        
        player = data["players"][0]
        
        # Check identity fields
        assert "uid" in player
        assert "name" in player
        assert "position" in player
        assert "age" in player
        assert "nationality" in player
        assert "club" in player
        
        # Check core attributes
        assert "ca" in player
        assert "pa" in player
        
        # Check technical attributes
        assert "dribbling" in player
        assert "finishing" in player
        assert "passing" in player
        
        # Check mental attributes
        assert "composure" in player
        assert "vision" in player
        assert "determination" in player
        
        # Check physical attributes
        assert "pace" in player
        assert "stamina" in player
        assert "strength" in player
        
        # Check financial
        assert "price" in player
        assert "wage" in player
        
        # Check physical stats
        assert "height" in player
        assert "weight" in player
        assert "left_foot" in player
        assert "right_foot" in player
