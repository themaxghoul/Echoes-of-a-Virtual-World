# AI Village: The Echoes - Deployment & Integration Guides

## Table of Contents
1. [Emergent to GitHub Workflow](#emergent-to-github)
2. [Local Development Setup](#local-development)
3. [Unity Integration Guide](#unity-integration)
4. [Test Running Guide](#test-running)

---

## <a name="emergent-to-github"></a>1. Emergent to GitHub Workflow

### Step 1: Save to GitHub from Emergent

1. **In the Emergent Chat Interface:**
   - Look for the **"Save to Github"** button in the chat input area
   - Click it to open the GitHub save dialog

2. **Connect Your GitHub Account:**
   - Authorize Emergent to access your GitHub
   - Select destination repository (or create new)

3. **Configure Save Options:**
   ```
   Repository: your-username/ai-village-echoes
   Branch: main (or create new branch)
   Commit Message: "Deploy from Emergent - [date]"
   ```

4. **Save and Push:**
   - Click "Save to GitHub"
   - Wait for confirmation message

### Step 2: Clone and Run Locally

```bash
# Clone the repository
git clone https://github.com/your-username/ai-village-echoes.git
cd ai-village-echoes

# Backend Setup
cd backend
python -m venv venv
source venv/bin/activate  # Windows: venv\Scripts\activate
pip install -r requirements.txt

# Create .env file
cat > .env << EOF
MONGO_URL=mongodb://localhost:27017
DB_NAME=ai_village_echoes
LLM_API_KEY=your_emergent_llm_key
EOF

# Start MongoDB (Docker recommended)
docker run -d -p 27017:27017 --name mongodb mongo:6

# Run Backend
uvicorn server:app --host 0.0.0.0 --port 8001 --reload

# Frontend Setup (new terminal)
cd ../frontend
yarn install  # or npm install
cat > .env << EOF
REACT_APP_BACKEND_URL=http://localhost:8001
EOF

yarn start
```

### Step 3: Environment Variables Reference

**Backend (.env):**
```env
MONGO_URL=mongodb://localhost:27017
DB_NAME=ai_village_echoes
LLM_API_KEY=<your_emergent_universal_key>
STRIPE_SECRET_KEY=<optional_for_payments>
UNITY_SERVER_URL=wss://your-unity-server.com
```

**Frontend (.env):**
```env
REACT_APP_BACKEND_URL=http://localhost:8001
```

---

## <a name="local-development"></a>2. Local Development Setup

### Prerequisites
- Python 3.11+
- Node.js 18+
- MongoDB 6+
- Yarn (recommended over npm)

### Quick Start Script

Create `start-dev.sh`:
```bash
#!/bin/bash

# Start MongoDB
echo "Starting MongoDB..."
docker run -d -p 27017:27017 --name mongodb mongo:6 2>/dev/null || docker start mongodb

# Start Backend
echo "Starting Backend..."
cd backend
source venv/bin/activate
uvicorn server:app --host 0.0.0.0 --port 8001 --reload &
BACKEND_PID=$!

# Wait for backend
sleep 3

# Start Frontend
echo "Starting Frontend..."
cd ../frontend
yarn start &
FRONTEND_PID=$!

echo ""
echo "==================================="
echo "AI Village: The Echoes - Running!"
echo "==================================="
echo "Backend:  http://localhost:8001"
echo "Frontend: http://localhost:3000"
echo "API Docs: http://localhost:8001/docs"
echo ""
echo "Press Ctrl+C to stop all services"

# Wait for interrupt
trap "kill $BACKEND_PID $FRONTEND_PID 2>/dev/null" EXIT
wait
```

### API Documentation
Access Swagger docs at: `http://localhost:8001/docs`

Key endpoints:
- `/api/auth/login` - Authentication
- `/api/characters` - Character management
- `/api/rt-tasks/*` - Real-time micro-tasks
- `/api/economy/*` - Currency & compute
- `/api/world-map/*` - World data
- `/api/building/*` - 2D building system

---

## <a name="unity-integration"></a>3. Unity Integration Guide

### Overview
The Echoes uses a **descriptor-based system** for 3D models. Unity interprets JSON descriptors to generate characters and world elements.

### Step 1: Unity Project Setup

1. **Create New Unity Project:**
   - Unity 2022.3 LTS or later
   - 3D (URP) template recommended

2. **Install Required Packages:**
   ```
   Window > Package Manager
   - Newtonsoft JSON (com.unity.nuget.newtonsoft-json)
   - WebSocket Sharp (via NuGet or manual)
   ```

3. **Project Structure:**
   ```
   Assets/
   ├── Scripts/
   │   ├── Network/
   │   │   ├── EchoesClient.cs
   │   │   └── SessionManager.cs
   │   ├── Characters/
   │   │   ├── CharacterGenerator.cs
   │   │   └── ModelDescriptor.cs
   │   └── World/
   │       ├── WorldMapLoader.cs
   │       └── TerrainGenerator.cs
   ├── Prefabs/
   │   ├── Characters/
   │   └── Buildings/
   └── Resources/
       └── CharacterParts/
   ```

### Step 2: Character Model Descriptor System

**ModelDescriptor.cs:**
```csharp
using System;
using Newtonsoft.Json;

[Serializable]
public class CharacterModelDescriptor
{
    public string bodyType;      // athletic, muscular, slender, stocky, average
    public string faceType;      // angular, round, oval, square, heart
    public string skinTone;      // pale, fair, medium, olive, tan, brown, dark, ebony
    public string hairStyle;     // short, medium, long, bald, braided, ponytail, mohawk, curly
    public string hairColor;     // black, brown, blonde, red, gray, white, blue, purple
    public string eyeColor;      // brown, blue, green, hazel, gray, amber, violet
    public string clothingStyle; // adventurer, noble, mage, warrior, merchant, peasant, rogue, tribal
    public int height;           // 140-220 cm
    public int age;              // 16-100
    public bool scars;
    public bool tattoos;
    public bool beard;
    public string[] accessories;
    
    public static CharacterModelDescriptor FromJson(string json)
    {
        return JsonConvert.DeserializeObject<CharacterModelDescriptor>(json);
    }
}
```

**CharacterGenerator.cs:**
```csharp
using UnityEngine;

public class CharacterGenerator : MonoBehaviour
{
    [Header("Body Type Prefabs")]
    public GameObject[] bodyTypePrefabs; // Index: 0=athletic, 1=muscular, etc.
    
    [Header("Face Meshes")]
    public Mesh[] faceMeshes;
    
    [Header("Hair Prefabs")]
    public GameObject[] hairPrefabs;
    
    [Header("Clothing Sets")]
    public GameObject[] clothingSets;
    
    public GameObject GenerateCharacter(CharacterModelDescriptor descriptor)
    {
        // 1. Instantiate base body
        int bodyIndex = GetBodyTypeIndex(descriptor.bodyType);
        GameObject character = Instantiate(bodyTypePrefabs[bodyIndex]);
        
        // 2. Apply skin tone
        ApplySkinTone(character, descriptor.skinTone);
        
        // 3. Attach hair
        AttachHair(character, descriptor.hairStyle, descriptor.hairColor);
        
        // 4. Set eye color
        SetEyeColor(character, descriptor.eyeColor);
        
        // 5. Apply clothing
        ApplyClothing(character, descriptor.clothingStyle);
        
        // 6. Scale for height
        float scale = descriptor.height / 170f; // 170cm as base
        character.transform.localScale = Vector3.one * scale;
        
        // 7. Apply features (scars, tattoos, beard)
        if (descriptor.scars) ApplyScars(character);
        if (descriptor.tattoos) ApplyTattoos(character);
        if (descriptor.beard) ApplyBeard(character);
        
        return character;
    }
    
    // Implementation methods...
    private int GetBodyTypeIndex(string type) => type switch
    {
        "athletic" => 0,
        "muscular" => 1,
        "slender" => 2,
        "stocky" => 3,
        _ => 4 // average
    };
    
    private void ApplySkinTone(GameObject obj, string tone)
    {
        Color color = tone switch
        {
            "pale" => new Color(1f, 0.89f, 0.82f),
            "fair" => new Color(0.96f, 0.82f, 0.71f),
            "medium" => new Color(0.83f, 0.65f, 0.46f),
            "olive" => new Color(0.77f, 0.64f, 0.35f),
            "tan" => new Color(0.65f, 0.49f, 0.32f),
            "brown" => new Color(0.55f, 0.35f, 0.17f),
            "dark" => new Color(0.36f, 0.25f, 0.22f),
            _ => new Color(0.24f, 0.15f, 0.14f) // ebony
        };
        
        var renderer = obj.GetComponentInChildren<SkinnedMeshRenderer>();
        if (renderer != null)
        {
            renderer.material.color = color;
        }
    }
    
    // ... other implementation methods
}
```

### Step 3: Network Connection

**EchoesClient.cs:**
```csharp
using System;
using System.Collections;
using UnityEngine;
using UnityEngine.Networking;
using Newtonsoft.Json;

public class EchoesClient : MonoBehaviour
{
    public static EchoesClient Instance;
    
    [Header("Server Configuration")]
    public string serverUrl = "https://your-server.com/api";
    public string sessionToken;
    
    private void Awake()
    {
        Instance = this;
        DontDestroyOnLoad(gameObject);
    }
    
    // Connect with session code from web
    public IEnumerator ConnectWithSession(string sessionCode)
    {
        string url = $"{serverUrl}/unity/session/{sessionCode}/connect";
        
        using (UnityWebRequest request = UnityWebRequest.Post(url, ""))
        {
            request.SetRequestHeader("Content-Type", "application/json");
            
            yield return request.SendWebRequest();
            
            if (request.result == UnityWebRequest.Result.Success)
            {
                var response = JsonConvert.DeserializeObject<SessionResponse>(request.downloadHandler.text);
                sessionToken = response.token;
                Debug.Log("Connected to The Echoes!");
            }
            else
            {
                Debug.LogError($"Connection failed: {request.error}");
            }
        }
    }
    
    // Fetch character data
    public IEnumerator GetCharacter(string characterId, Action<CharacterModelDescriptor> callback)
    {
        string url = $"{serverUrl}/character/{characterId}";
        
        using (UnityWebRequest request = UnityWebRequest.Get(url))
        {
            yield return request.SendWebRequest();
            
            if (request.result == UnityWebRequest.Result.Success)
            {
                var data = JsonConvert.DeserializeObject<CharacterData>(request.downloadHandler.text);
                callback?.Invoke(data.model);
            }
        }
    }
    
    // Sync state back to server
    public IEnumerator SyncState(SyncData data)
    {
        string url = $"{serverUrl}/unity/sync";
        string json = JsonConvert.SerializeObject(data);
        
        using (UnityWebRequest request = UnityWebRequest.Post(url, json))
        {
            request.SetRequestHeader("Content-Type", "application/json");
            request.SetRequestHeader("Authorization", $"Bearer {sessionToken}");
            
            yield return request.SendWebRequest();
        }
    }
}

[Serializable]
public class SessionResponse
{
    public string session_id;
    public string token;
}

[Serializable]
public class CharacterData
{
    public string id;
    public string name;
    public CharacterModelDescriptor model;
}

[Serializable]
public class SyncData
{
    public string session_id;
    public Vector3 position;
    public float health;
    public int experience;
}
```

### Step 4: World Map Loading

**WorldMapLoader.cs:**
```csharp
using System.Collections;
using UnityEngine;
using UnityEngine.Networking;
using Newtonsoft.Json;

public class WorldMapLoader : MonoBehaviour
{
    public string worldId = "main-story-realm";
    public TerrainGenerator terrainGenerator;
    
    public IEnumerator LoadWorld()
    {
        string url = $"{EchoesClient.Instance.serverUrl}/world-map/{worldId}";
        
        using (UnityWebRequest request = UnityWebRequest.Get(url))
        {
            yield return request.SendWebRequest();
            
            if (request.result == UnityWebRequest.Result.Success)
            {
                var worldData = JsonConvert.DeserializeObject<WorldMapData>(request.downloadHandler.text);
                
                // Generate terrain from seed
                terrainGenerator.GenerateFromSeed(worldData.seed, worldData.width, worldData.height);
                
                // Apply region data
                foreach (var region in worldData.regions)
                {
                    terrainGenerator.ApplyRegion(region.Key, region.Value);
                }
                
                // Place buildings
                foreach (var building in worldData.buildings)
                {
                    PlaceBuilding(building);
                }
                
                Debug.Log($"World loaded: {worldData.regions.Count} regions");
            }
        }
    }
    
    private void PlaceBuilding(BuildingData building)
    {
        // Instantiate building prefab at position
        string prefabPath = $"Buildings/{building.building_type}";
        GameObject prefab = Resources.Load<GameObject>(prefabPath);
        
        if (prefab != null)
        {
            Vector3 pos = new Vector3(building.position[0], 0, building.position[1]);
            Instantiate(prefab, pos, Quaternion.Euler(0, building.rotation, 0));
        }
    }
}
```

---

## <a name="test-running"></a>4. Test Running Guide

### Backend Testing

```bash
cd backend

# Install test dependencies
pip install pytest pytest-asyncio httpx

# Run all tests
pytest tests/ -v

# Run specific test file
pytest tests/test_p1_features.py -v

# Run with coverage
pytest tests/ --cov=. --cov-report=html
```

### API Testing with curl

```bash
# Set API URL
API_URL="http://localhost:8001/api"

# 1. Login
TOKEN=$(curl -s -X POST "$API_URL/auth/login" \
  -H "Content-Type: application/json" \
  -d '{"username":"sirix_1","password":"HCLynnTV04"}' | jq -r '.token')

# 2. Create Character
curl -X POST "$API_URL/characters" \
  -H "Content-Type: application/json" \
  -d '{
    "user_id": "test-user",
    "name": "Test Hero",
    "background": "A test character",
    "model": {
      "bodyType": "athletic",
      "skinTone": "medium",
      "hairStyle": "short"
    }
  }'

# 3. Start RT Task Session
curl -X POST "$API_URL/rt-tasks/session/start" \
  -H "Content-Type: application/json" \
  -d '{
    "worker_id": "test-user",
    "task_type": "sentiment_label"
  }'

# 4. Get Economy Stats
curl -s "$API_URL/economy/stats/overview"
```

### Unity Testing

1. **Open Unity Test Runner:**
   - Window > General > Test Runner

2. **Create Test Script:**
```csharp
using NUnit.Framework;
using UnityEngine;

public class CharacterTests
{
    [Test]
    public void CharacterDescriptor_ParsesCorrectly()
    {
        string json = @"{
            ""bodyType"": ""athletic"",
            ""skinTone"": ""medium"",
            ""height"": 180
        }";
        
        var descriptor = CharacterModelDescriptor.FromJson(json);
        
        Assert.AreEqual("athletic", descriptor.bodyType);
        Assert.AreEqual("medium", descriptor.skinTone);
        Assert.AreEqual(180, descriptor.height);
    }
    
    [Test]
    public void CharacterGenerator_CreatesObject()
    {
        var generator = new GameObject().AddComponent<CharacterGenerator>();
        var descriptor = new CharacterModelDescriptor
        {
            bodyType = "average",
            skinTone = "fair",
            height = 170
        };
        
        // This would need prefabs set up
        // var character = generator.GenerateCharacter(descriptor);
        // Assert.IsNotNull(character);
    }
}
```

3. **Run Tests:**
   - Click "Run All" in Test Runner window
   - Or use command line: `Unity -runTests -projectPath . -testResults results.xml`

### Frontend Testing

```bash
cd frontend

# Run Jest tests
yarn test

# Run with coverage
yarn test --coverage

# E2E tests (if configured)
yarn test:e2e
```

---

## Quick Reference

### Admin Credentials
- **Username:** `sirix_1`
- **Password:** `HCLynnTV04`

### Key URLs (Local)
- Frontend: `http://localhost:3000`
- Backend: `http://localhost:8001`
- API Docs: `http://localhost:8001/docs`

### Key URLs (Emergent Preview)
- Full App: `https://your-app.preview.emergentagent.com`
- API: `https://your-app.preview.emergentagent.com/api`

### Support
- Emergent Platform: [emergent.sh](https://emergent.sh)
- GitHub Issues: Create issue in your repo
