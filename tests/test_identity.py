from core.identity import commitment_key

def test_same_commitment_same_key():
    # same owner + same normalized action -> same key (merge case)
    a = commitment_key(owner="Alex Vetsak", action="Send Prathik the Jakarta itinerary")
    b = commitment_key(owner="alex vetsak",  action="send prathik the jakarta itinerary.")
    assert a == b

def test_different_action_different_key():
    a = commitment_key(owner="Alex Vetsak", action="Send Prathik the Jakarta itinerary")
    b = commitment_key(owner="Alex Vetsak", action="Send Prathik the German proposal")
    assert a != b

def test_different_owner_different_key():
    
    a = commitment_key(owner="Prathik Prasad", action="Send Prathik the Jakarta itinerary")
    b = commitment_key(owner="Alex Vetsak", action="Send Prathik the Jakarta itinerary")
    assert a != b

def test_key_is_stable():

    a = commitment_key(owner="Alex Vetsak", action="Send Prathik the Jakarta itinerary")
    b = commitment_key(owner="Alex Vetsak", action="Send Prathik the Jakarta itinerary")
    assert a == b

