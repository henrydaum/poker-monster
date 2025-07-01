from flask import Flask, render_template, redirect, url_for, session
# Import information needed to rewrite run_game() for a server
from poker_monster import build_decks, Player, GameState, create_action

# Need to store the gamestate and the previous AI hidden state in the session (like a cache)

app = Flask(__name__)
# A secret key is required to use sessions
app.secret_key = 'a_very_secret_key' 

@app.route("/")
def index():
    """Initial route to start a new game."""
    # Need to ask user if they want to play Hero or Monster

    # Build decks and create player instances
    hero_deck, monster_deck = build_decks()
    hero = Player("hero", hero_deck, "person")
    monster = Player("monster", monster_deck, "computer_ai") # Or any other type

    # coin flip to see who goes first
    coin_flip = randint(0, 1)
    going_first = None
    if coin_flip == 0:  # Heads is for Monster, obviously
        going_first = "monster"
        monster.going_first = True
    else:
        going_first = "hero"
        hero.going_first = True
    
    # Create and configure the initial game state
    gs = GameState(hero, monster, turn_priority=going_first) # Assuming hero starts
    gs.hero.shuffle()
    gs.monster.shuffle()
    gs.hero.draw(4)
    gs.monster.draw(4)
    
    if gs.me.player_type.startswith("computer_ai"):
        while gs.me.player_type.startswith("computer_ai"):
            # AI takes turns until it is the user's turn

    # Store the game state object in the session
    session['game_state'] = gs.to_dict() # You'll need to add a to_dict() method

    return redirect(url_for('display_gamestate'))

# Turns gamestate into HTML
@app.route("/gamestate")
def display_gamestate():
    """Displays the main game board."""
    # Load game state from the session
    if 'game_state' not in session:
        return redirect(url_for('index'))

    gs = GameState.from_dict(session['game_state']) # You'll need a from_dict() method

    # Check for a winner
    if gs.winner:
        return render_template('winner.html', winner=gs.winner)

    # Use your existing functions to get display data
    game_info = get_game_info(gs) # A helper to package data from display_info
    available_actions = get_available_actions(gs) # A helper to get legal actions

    return render_template('game.html', info=game_info, actions=available_actions)

# Turns HTML into an action
@app.route("/action/<int:action_id>")
def do_action(action_id):
    """Handles a player's action."""
    if 'game_state' not in session:
        return redirect(url_for('index'))
    
    gs = GameState.from_dict(session['game_state'])

    # Create and execute the action
    action = create_action(gs, action_id)
    legal, reason = action.is_legal()
    
    if legal:
        action.enact()
        # After the action, AI might take a turn if it's their turn
        # This part of your logic might need adjustment for a web interface
    else:
        # Optionally, you can pass an error message to the user
        session['error_message'] = reason
    
    if gs.me.player_type.startswith("computer_ai"):
        while gs.me.player_type.startswith("computer_ai"):
            # AI takes turns until it is the user's turn

    # Save the updated game state back to the session
    session['game_state'] = gs.to_dict()
    
    return redirect(url_for('display_gamestate'))

if __name__ == "__main__":
    app.run(debug=True)