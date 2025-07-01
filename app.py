from flask import Flask, render_template, redirect, url_for, session, request
from flask_session import Session
import torch
import random
from poker_monster import (
    Network, create_action, GameState, Player, build_decks, 
    hyperparameters, num_actions, 
    PHASE_AWAITING_INPUT, PHASE_PLAYING_SELECTED_CARD, PHASE_VIEWING_CARD_INFO,
    PHASE_SELECTING_GRAVEYARD_CARD, PHASE_REORDERING_DECK_TOP3, PHASE_DISCARDING_CARD_FROM_OPP_HAND,
    PHASE_CHOOSING_GO_ALL_IN_TARGET, PHASE_CHOOSING_FOLD_TARGET, PHASE_CHOOSING_POKER_FACE_TARGET,
    PHASE_CHOOSING_CHEAP_SHOT_TARGET, PHASE_CHOOSING_ULTIMATUM_CARD, PHASE_OPP_CHOOSING_FROM_ULTIMATUM,
    PHASE_CHOOSING_FROM_DECK_TOP2, PHASE_HAND_FULL_DISCARDING_CARD
)

app = Flask(__name__)
# A secret key is required to use sessions
app.secret_key = 'a_very_secret_key'

# This uses Flask Session to run the cookie on the server side (the gamestate + hidden state is too large for browser)
app.config["SESSION_PERMANENT"] = False
app.config["SESSION_TYPE"] = "filesystem"
Session(app)

device = torch.device("cuda" if torch.cuda.is_available() else "cpu")
hero_ai = Network(name="hero", **hyperparameters)
monster_ai = Network(name="monster", **hyperparameters)
hero_ai.to(device)
monster_ai.to(device)

try:
    hero_ai.load("hero")
except Exception as e:
    print(f"Could not load hero_ai: {e}")
try:
    monster_ai.load("monster")
except Exception as e:
    print(f"Could not load monster_ai: {e}")

def serialize_hidden_state(state_tuple):
    """Converts a PyTorch hidden state tuple into a serializable list tuple."""
    h_n_tensor, c_n_tensor = state_tuple
    return (h_n_tensor.tolist(), c_n_tensor.tolist())

def deserialize_hidden_state(state_lists):
    """Converts a list tuple from the session back into a PyTorch hidden state."""
    if not state_lists:
        return None
    h_n_list, c_n_list = state_lists
    h_n_tensor = torch.tensor(h_n_list).to(device)
    c_n_tensor = torch.tensor(c_n_list).to(device)
    return (h_n_tensor, c_n_tensor)

def take_ai_turn(gs, prev_hidden_state):
    """Processes the AI's turn, managing its hidden state."""
    # This loop handles cases where the AI might take multiple actions in a row
    while gs.winner is None and gs.me.player_type.startswith("computer_ai"):
        current_ai = hero_ai if gs.me.name == "hero" else monster_ai
        
        choice_number, new_hidden_state = current_ai.sample_action(gs, prev_hidden_state, training=False)
        prev_hidden_state = new_hidden_state # Use the new state for the next potential loop

        action = create_action(gs, choice_number)
        action.enact() # This function modifies gs in place

    return gs, new_hidden_state

def get_display_info(gs):
    """Packages all relevant GameState data into a dictionary for the template."""
    
    # Base player information
    info = {
        "turn_number": gs.turn_number,
        "turn_priority": gs.turn_priority,
        "game_phase": gs.game_phase,
        "me": {
            "name": gs.me.name, "health": gs.me.health, "power": gs.me.power,
            "deck_size": len(gs.me.deck),
            "hand": [c.to_dict() for c in gs.me.hand],
            "power_cards": [c.to_dict() for c in gs.me.power_cards],
            "battlefield": [c.to_dict() for c in gs.me.battlefield],
            "graveyard": [c.to_dict() for c in gs.me.graveyard]
        },
        "opp": {
            "name": gs.opp.name, "health": gs.opp.health, "power": gs.opp.power,
            "deck_size": len(gs.opp.deck),
            "hand_size": len(gs.opp.hand),
            "power_cards_size": len(gs.opp.power_cards),
            "battlefield": [c.to_dict() for c in gs.opp.battlefield],
            "graveyard": [c.to_dict() for c in gs.opp.graveyard]
        },
        "special_info": None # Placeholder for conditional information
    }

    # Add conditional info based on game phase, mimicking your display_info function
    if gs.game_phase == PHASE_REORDERING_DECK_TOP3:
        top_cards = [c.to_dict() for c in gs.me.deck[:3]]
        info['special_info'] = f"Reordering Top 3 Cards: {', '.join([c['name'] for c in top_cards])}"

    # Add more 'if' statements here for other phases like Peek, Ultimatum, etc.

    return info

def get_available_actions(gs):
    actions = []
    # FIX: Increased range to cover all potential actions
    for i in range(num_actions):
        action = create_action(gs, i)
        if action.is_legal()[0]:
            action_name = type(action).__name__
            if hasattr(action, 'resolving_card') and action.resolving_card:
                action_name += f": {action.resolving_card.name}"
            actions.append({"id": i, "name": action_name})
    return actions

@app.route("/")
def choice_screen():
    # Pop the winner from the session if it exists, so it only shows once.
    winner = session.pop('winner', None)
    return render_template('index.html', winner=winner)

@app.route("/start_game")
def start_game():
    """Initializes a new game based on the user's role choice."""
    user_role = request.args.get("role")

    if user_role == 'hero':
        hero_player_type, monster_player_type = "person", "computer_ai"
    elif user_role == 'monster':
        hero_player_type, monster_player_type = "computer_ai", "person"
    else:
        return redirect(url_for("choice_screen"))
    
    hero_deck, monster_deck = build_decks()
    hero = Player("hero", hero_deck, hero_player_type)
    monster = Player("monster", monster_deck, monster_player_type)
    
    going_first = "hero" if random.randint(0, 1) == 1 else "monster"
    if going_first == "hero":
        hero.going_first = True
    else:
        monster.going_first = True
    
    gs = GameState(hero, monster, going_first, PHASE_AWAITING_INPUT, cache=[], game_mode=0)
    gs.hero.shuffle()
    gs.monster.shuffle()
    gs.hero.draw(4)
    gs.monster.draw(4)

    # Initialize a blank hidden state for the AIs
    h0 = torch.zeros(hyperparameters["num_lstm_layers"], hyperparameters["lstm_size"])
    c0 = torch.zeros(hyperparameters["num_lstm_layers"], hyperparameters["lstm_size"])
    hidden_state = (h0, c0)

    # If the AI goes first, let it take its turn now
    if gs.me.player_type.startswith("computer_ai"):
        gs, hidden_state = take_ai_turn(gs, hidden_state)

    # Store the initial game and AI states in the session
    session["gs"] = gs.to_dict()
    session["hidden_state"] = serialize_hidden_state(hidden_state)
    
    return redirect(url_for("game"))

@app.route("/game")
def game():
    if "gs" not in session:
        return redirect(url_for("choice_screen"))

    gs = GameState.from_dict(session["gs"])

    if gs.winner:
        session['winner'] = gs.winner
        return redirect(url_for("choice_screen"))
    
    # Get the necessary info to display
    game_info = get_display_info(gs)
    available_actions = get_available_actions(gs)
    
    return render_template("game.html", info=game_info, actions=available_actions)

@app.route("/submit_action", methods=["POST"])
def submit_action():
    if "gs" not in session:
        return redirect(url_for("choice_screen"))
    
    # Load state from session
    gs = GameState.from_dict(session["gs"])
    hidden_state = deserialize_hidden_state(session.get("hidden_state"))

    # Get action_id from the form submission
    action_id = int(request.form["action_id"])
    print(f"Action ID chosen: {action_id}")

    # Execute the user's action
    action = create_action(gs, action_id)
    legal, reason = action.is_legal()
    if legal:
        action.enact() # This updates gs
    else:
        session["error"] = reason

    # If the game isn't over, let the AI take its turn
    if gs.winner is None and gs.me.player_type.startswith("computer_ai"):
        gs, hidden_state = take_ai_turn(gs, hidden_state)

    if gs.winner:
        # If there's a winner, store it in the session and redirect to the main page
        session["winner"] = gs.winner
        return redirect(url_for("choice_screen"))
    else:
        # If no winner, save the updated state and redirect back to the game board
        session["gs"] = gs.to_dict()
        session["hidden_state"] = serialize_hidden_state(hidden_state)
        return redirect(url_for("game"))

if __name__ == "__main__":
    app.run(debug=True)