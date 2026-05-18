"""Multi-user isolation: 3 users register, each creates a career,
each only sees their own careers."""
import json, urllib.request

BASE = "http://localhost:8000/api"


def req(method, path, body=None, token=None):
    data = json.dumps(body).encode() if body is not None else None
    headers = {"Content-Type": "application/json"} if body else {}
    if token:
        headers["Authorization"] = f"Bearer {token}"
    r = urllib.request.Request(BASE + path, data=data, method=method, headers=headers)
    try:
        with urllib.request.urlopen(r, timeout=60) as resp:
            return resp.status, json.loads(resp.read().decode())
    except urllib.error.HTTPError as e:
        return e.code, json.loads(e.read().decode() or "{}")


def step(n, m): print(f"\n  [{n}] {m}")
def assert_(c, m):
    print(f"      {'✓' if c else '✗'} {m}")
    if not c: raise AssertionError(m)


def main():
    print("\n  MULTI-USER ISOLATION TEST\n")

    # Register 3 users.
    tokens = {}
    for name in ("alice", "bob", "carol"):
        s, b = req("POST", "/auth/register", {
            "email": f"{name}@test.com", "password": "password1234", "name": name,
        })
        assert_(s == 200, f"register {name}: {s} {b}")
        tokens[name] = b["access_token"]
        print(f"      {name} → token={tokens[name][:20]}...")

    # Each creates a different career.
    careers = {}
    for name, club_id in (("alice", 21), ("bob", 22), ("carol", 1)):
        s, b = req("POST", "/careers", {
            "manager_name": name.title(), "club_id": club_id, "formation": "4-3-3",
        }, token=tokens[name])
        assert_(s == 201, f"{name} creates career: {s} {b}")
        careers[name] = b["id"]
        print(f"      {name} got career_id={b['id']} for {b['club_name']}")

    # Now check: alice can read her own career, but NOT bob's.
    step(2, "Alice reads her own career → 200")
    s, b = req("GET", f"/careers/{careers['alice']}", token=tokens["alice"])
    assert_(s == 200, f"alice → her career: {s}")
    assert_(b.get("club_name") == "R. Madrid", "alice → R. Madrid")

    step(3, "Alice tries Bob's career → 403")
    s, b = req("GET", f"/careers/{careers['bob']}", token=tokens["alice"])
    assert_(s == 403, f"alice cannot read bob's career: got {s}")

    step(4, "Bob reads his own → 200")
    s, b = req("GET", f"/careers/{careers['bob']}", token=tokens["bob"])
    assert_(s == 200, "bob reads his")
    assert_(b.get("club_name") == "Barcelona", "bob → Barcelona")

    step(5, "Carol creates a NEW career — only HER previous one wiped, not others")
    s, b = req("POST", "/careers", {
        "manager_name": "Carol", "club_id": 23, "formation": "4-3-3",
    }, token=tokens["carol"])
    assert_(s == 201, "carol's new career created")
    new_carol = b["id"]
    print(f"      carol's new career_id={new_carol}")

    # Bob's career should still exist.
    s, b = req("GET", f"/careers/{careers['bob']}", token=tokens["bob"])
    assert_(s == 200, f"bob's career SURVIVED carol's wipe (got {s})")
    assert_(b.get("club_name") == "Barcelona", "bob still has Barcelona")

    # Alice's career should still exist.
    s, b = req("GET", f"/careers/{careers['alice']}", token=tokens["alice"])
    assert_(s == 200, "alice's career SURVIVED carol's wipe")

    print(f"\n  ALL MULTI-USER CHECKS PASSED.\n")


if __name__ == "__main__":
    main()
