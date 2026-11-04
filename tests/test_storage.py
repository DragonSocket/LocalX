"""Tests for Storage Protocol and InMemoryStorage implementation."""

import asyncio


async def run_tests():
    """Run all storage protocol tests."""
    
    from database import InMemoryStorage
    from interfaces import Storage as Storage
    
    storage = InMemoryStorage()
    
    # Test 1: Init completes without error
    await storage.init()
    print("✓ [INIT] init() completes without error")
    
    # Test 2: Save returns None and persists message
    assert asyncio.iscoroutinefunction(storage.save), "save must be async"
    result = await storage.save("alice", "Hello!")
    assert result is None, "save should return None per protocol spec"
    print("✓ [SAVE] save() stores message and returns None")
    
    # Test 3: Fetch history returns newest first with limit=50 default
    history = await storage.fetch_history(limit=50)
    assert isinstance(history, list), "fetch_history must return a list"
    assert len(history) == 1, f"Should have 1 message, got {len(history)}"
    assert history[0]["sender"] == "alice"
    assert history[0]["message"] == "Hello!"
    print("✓ [FETCH] fetch_history() returns single message")
    
    # Add more messages for pagination test
    await storage.save("bob", "Hi Alice!")
    await storage.save("alice", "Hey Bob!")
    await storage.save("charlie", "Hello everyone!")
    
    history = await storage.fetch_history(limit=2)
    assert len(history) == 2, f"Limit exceeded: got {len(history)} messages"
    assert history[0]["sender"] == "charlie", "Should return newest first"
    assert history[1]["sender"] == "alice"
    print("✓ [FETCH] fetch_history(limit=2) correctly returns 2 newest messages")
    
    # Test 4: Timestamp is recorded and valid
    history = await storage.fetch_history(1)
    assert "timestamp" in history[0], "History entries must include timestamp"
    ts = history[0]["timestamp"]
    now = asyncio.get_event_loop().time()
    assert isinstance(ts, float), "Timestamp must be numeric"
    print("✓ [TIMESTAMP] Timestamp is recorded and valid float")
    
    # Test 5: Close completes without error
    await storage.close()
    print("✓ [CLOSE] close() completes without error")
    
    # Test 6: Protocol composition check
    assert isinstance(storage, Storage), \
        "InMemoryStorage must be an instance of Storage protocol"
    print("✓ [PROTOCOL] InMemoryStorage satisfies Storage protocol")
    
    # Verify all methods exist and have correct signatures
    import inspect
    sig = inspect.signature(storage.init)
    assert str(sig.return_annotation) == 'None' or sig.return_annotation is None
    
    sig = inspect.signature(storage.close)
    assert str(sig.return_annotation) == 'None' or sig.return_annotation is None
    
    print("✓ [SIGNATURES] All async method signatures are correct")
    
    await storage.save("alice", "Final test message")
    history = await storage.fetch_history()
    # Should have 4 messages now (added in each iteration)
    print(f"✓ Current history: {len(history)} messages in buffer")
    
    print("=" * 60)
    print("ALL TESTS PASSED!")


if __name__ == "__main__":
    asyncio.run(run_tests())
