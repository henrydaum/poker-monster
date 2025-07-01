from flask import Flask, render_template, redirect, url_for, session, request
import torch
from poker_monster import Network, create_action, GameState, Player, hyperparameters

app = Flask(__name__)
# A secret key is required to use sessions
app.secret_key = 'a_very_secret_key'

device = torch.device("cuda" if torch.cuda.is_available() else "cpu")
hero_ai = Network(name="hero", **hyperparameters)
monster_ai = Network(name="monster", **hyperparameters)

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
    # (e.g., if it draws a card that lets it play another card)
    while gs.winner is None and gs.me.player_type.startswith("computer_ai"):
        current_ai = hero_ai if gs.me.name == "hero" else monster_ai
        
        choice_number, new_hidden_state = current_ai.sample_action(gs, prev_hidden_state, training=False)
        prev_hidden_state = new_hidden_state # Use the new state for the next potential loop

        action = create_action(gs, choice_number)
        action.enact() # This function modifies gs in place

    return gs, new_hidden_state

@app.route("/")
def choice_screen():
    """Displays the initial screen for the user to choose their role."""
    session.clear() # Clear any old game data before starting a new one
    return render_template('choice.html')

@app.route("/start_game")
def start_game():
    """Initializes a new game based on the user's role choice."""
    user_role = request.args.get('role')

    # FIX: Use assignment (=) instead of comparison (==)
    if user_role == 'hero':
        hero_player_type = "person"
        monster_player_type = "computer_ai"
    elif user_role == 'monster':
        hero_player_type = "computer_ai"
        monster_player_type = "person"
    else:
        return redirect(url_for('choice_screen'))
    
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
    
    return redirect(url_for('display_gs'))

@app.route("/gs")
def display_gs():
    """Displays the current game state and possible actions."""
    if 'gs' not in session:
        return redirect(url_for("choice_screen"))

    gs = gs.from_dict(session["gs"])

    if gs.winner:
        return render_template("winner.html", winner=gs.winner)
    
    # Get the necessary info to display
    game_info = get_display_info(gs)
    available_actions = get_available_actions(gs)
    
    return render_template("game.html", info=game_info, actions=available_actions)

@app.route("/action/<int:action_id>")
def do_action(action_id):
    """Handles a user's action, then processes the AI's turn."""
    if 'gs' not in session:
        return redirect(url_for("choice_screen"))
    
    # Load both the game state and the AI's hidden state
    gs = gs.from_dict(session["gs"])
    hidden_state = deserialize_hidden_state(session.get("hidden_state"))

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

    # Save the updated states back to the session
    session["gs"] = gs.to_dict()
    session["hidden_state"] = serialize_hidden_state(hidden_state)
    
    return redirect(url_for("display_gs"))

if __name__ == "__main__":
    app.run(debug=True)