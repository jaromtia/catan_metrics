# Appendix A — Catan Rules Reference

This is the subset of rules the engine enforces. See the official Catan rulebook for full details.

---

## Setup Phase (Snake Draft)

1. Players take turns in order placing one settlement, then one adjacent road.
2. Then in **reverse** order, each places their second settlement and one adjacent road.
3. The **second** settlement triggers immediate resource collection from all adjacent hexes.

Example with 3 players (Alice, Bob, Charlie):
```
Round 1: Alice → Bob → Charlie
Round 2: Charlie → Bob → Alice
```

The app tracks this automatically — players just click where they want to build.

---

## Main Game Turn Order

1. **Roll dice** (mandatory first action)
2. **If 7 rolled:**
   - Any player with > 7 cards must discard half (rounded down)
   - Active player moves the robber to a new hex
   - Active player may steal 1 card from a player with a settlement/city on that hex
3. **If not 7:** All players with settlements/cities on hexes matching the roll collect resources
4. **Trade** (optional): bank trade, player trade
5. **Build** (optional): roads, settlements, cities, dev cards
6. **Play one dev card** (optional, one per turn, not the one bought this turn)
7. **End turn**

---

## Building Rules

### Road
- Cost: 1 BRICK + 1 LUMBER
- Must connect to your existing road, settlement, or city
- Opponent's settlement between two of your road segments **breaks** them for Longest Road purposes

### Settlement
- Cost: 1 BRICK + 1 LUMBER + 1 WOOL + 1 GRAIN
- Must be placed on a vertex with no adjacent buildings (distance rule)
- Must connect to your existing road (in main play phase)

### City (upgrades a settlement)
- Cost: 2 GRAIN + 3 ORE
- Replaces one of your settlements; produces 2 resources instead of 1

### Development Card
- Cost: 1 ORE + 1 WOOL + 1 GRAIN
- One dev card per turn (the card bought this turn cannot be played until next turn)

---

## Victory Conditions

First player to reach **10 victory points** wins.

| Source | VP |
|--------|-----|
| Settlement | 1 |
| City | 2 |
| Victory Point dev card | 1 (hidden until win) |
| Longest Road award | 2 |
| Largest Army award | 2 |

---

## Longest Road

- Minimum **5 continuous roads** to claim the award
- Another player can take it by building a longer continuous road
- Opponent's settlement in the middle of a road chain **splits** it
- Tie: current holder keeps the award

---

## Largest Army

- Minimum **3 knights played** to claim the award
- Another player can take it by playing **strictly more** knights than the current holder
- Tie: current holder keeps the award

---

## Bank Resources

- 19 cards of each resource (BRICK, LUMBER, WOOL, GRAIN, ORE)
- **Bank shortage rule:** if total player demand for a resource exceeds what's in the bank:
  - If one player demands it alone: they get `min(demand, available)`
  - If multiple players demand it: nobody gets any

---

## Development Card Deck

| Card | Count | Effect |
|------|-------|--------|
| Knight | 14 | Move robber, steal 1 card |
| Victory Point | 5 | +1 VP (hidden in hand) |
| Road Building | 2 | Place 2 roads for free |
| Year of Plenty | 2 | Take any 2 resources from bank |
| Monopoly | 2 | Take all of 1 resource from every other player |

Total: 25 cards.

---

## Port Trading

| Port | Trade ratio |
|------|-------------|
| No port | 4:1 any resource |
| 3:1 generic port | 3:1 any resource |
| 2:1 specific port | 2:1 for that resource |

---

## Robber Rules

- Robber starts on the desert hex
- When a 7 is rolled, the active player **must** move the robber to a different hex
- The robber blocks resource production on its hex
- The active player may steal 1 card from any player with a building on the robber's hex
- Knight cards let you move the robber any time in your turn (before or after rolling)
