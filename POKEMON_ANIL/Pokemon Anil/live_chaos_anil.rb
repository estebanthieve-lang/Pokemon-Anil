begin
  require "socket"
rescue LoadError
end

module LiveChaosAnil
  HOST = "127.0.0.1"
  PORT = 8798
  COMMAND_FILE = File.expand_path("live_chaos_queue.txt", File.dirname(__FILE__))
  LOG_FILE = File.expand_path("live_chaos_log.txt", File.dirname(__FILE__))

  @queue = []
  @mutex = Mutex.new
  @started = false
  @file_position = 0
  @lottery_no_targets_locked = false

  def self.log(message)
    File.open(LOG_FILE, "a") { |file| file.puts("#{Time.now} #{message}") } rescue nil
    MKXP.puts("[LiveChaosAnil] #{message}")
  rescue
  end

  def self.start
    return if @started
    @started = true
    log("starting")
    start_socket_server
    hook_scene_map
  end

  def self.start_socket_server
    Thread.new do
      begin
        server = TCPServer.new(HOST, PORT)
        log("listening on #{HOST}:#{PORT}")
        loop do
          client = server.accept
          begin
            line = client.gets.to_s.strip
            client.puts(handle_line(line))
          rescue => e
            client.puts("ERR #{e.class}: #{e.message}") rescue nil
          ensure
            client.close rescue nil
          end
        end
      rescue => e
        log("socket server failed: #{e.class}: #{e.message}")
      end
    end
  end

  def self.hook_scene_map
    Thread.new do
      begin
        sleep 0.25 until defined?(Scene_Map)
        Scene_Map.class_eval do
          unless method_defined?(:live_chaos_original_update)
            alias live_chaos_original_update update
          end

          def update(*args)
            LiveChaosAnil.process_queue
            live_chaos_original_update(*args)
          end
        end
        log("Scene_Map hooked")
      rescue => e
        log("Scene_Map hook failed: #{e.class}: #{e.message}")
      end
    end
  end

  def self.handle_line(line)
    parts = line.split(/\s+/)
    command = parts.shift.to_s
    case command
    when "add_item"
      item = parts.shift.to_s.upcase
      quantity = parts.shift.to_i
      quantity = 1 if quantity < 1
      quantity = 99 if quantity > 99
      raise "missing item" if item.empty?
      enqueue(:type => :add_item, :item => item, :quantity => quantity)
      "OK queued add_item #{item} #{quantity}"
    when "heal_party"
      enqueue(:type => :heal_party)
      "OK queued heal_party"
    when "pokemon_lottery_status"
      enqueue(:type => :pokemon_lottery_status)
      "OK queued pokemon_lottery_status"
    when "replace_all_party_with_random_pokedex_safe"
      enqueue(:type => :replace_all_party_with_random_pokedex_safe)
      "OK queued replace_all_party_with_random_pokedex_safe"
    else
      "ERR unknown_command #{command}"
    end
  rescue => e
    "ERR #{e.class}: #{e.message}"
  end

  def self.enqueue(payload)
    @mutex.synchronize { @queue << payload }
  end

  def self.process_queue
    poll_command_file
    loop do
      payload = nil
      @mutex.synchronize { payload = @queue.shift }
      break if payload.nil?
      execute(payload)
    end
  end

  def self.poll_command_file
    return unless File.exist?(COMMAND_FILE)
    File.open(COMMAND_FILE, "r") do |file|
      file.seek(@file_position, IO::SEEK_SET)
      file.each_line do |line|
        result = handle_line(line.strip)
        log(result)
      end
      @file_position = file.pos
    end
  rescue => e
    log("file bridge failed: #{e.class}: #{e.message}")
  end

  def self.execute(payload)
    case payload[:type]
    when :add_item
      add_item(payload[:item], payload[:quantity])
    when :heal_party
      heal_party
    when :pokemon_lottery_status
      pokemon_lottery_status
    when :replace_all_party_with_random_pokedex_safe
      replace_all_party_with_random_pokedex_safe
    end
  rescue => e
    log("command failed: #{e.class}: #{e.message}")
  end

  def self.add_item(item_name, quantity)
    item = item_name.to_sym
    if Object.respond_to?(:pbReceiveItem)
      pbReceiveItem(item, quantity)
    elsif defined?($bag) && $bag && $bag.respond_to?(:add)
      $bag.add(item, quantity)
    else
      raise "bag is not ready"
    end
    log("added #{quantity} #{item_name}")
  end

  def self.heal_party
    if Object.respond_to?(:pbHealAll)
      pbHealAll
    elsif defined?($player) && $player && $player.respond_to?(:party)
      $player.party.each { |pkmn| pkmn.heal if pkmn && pkmn.respond_to?(:heal) }
    else
      raise "party is not ready"
    end
    log("party healed")
  end

  def self.party
    return $player.party if defined?($player) && $player && $player.respond_to?(:party)
    nil
  end

  def self.status_pool
    frozen = defined?(GameData::Status) && GameData::Status.try_get(:FROZEN) ? :FROZEN : :FROSTBITE
    [
      [:PARALYSIS, "PAR", "Paralizados"],
      [:SLEEP, "DOR", "Dormidos"],
      [:BURN, "QUE", "Quemados"],
      [:POISON, "ENV", "Envenenados"],
      [frozen, "CON", "Congelados"]
    ]
  end

  def self.can_receive_status?(pkmn)
    return false unless pkmn
    return false if pkmn.respond_to?(:egg?) && pkmn.egg?
    return false if pkmn.respond_to?(:fainted?) && pkmn.fainted?
    if pkmn.respond_to?(:status)
      current = pkmn.status
      return false unless current.nil? || current == :NONE || current.to_s == "NONE" || current.to_s.empty?
    end
    true
  end

  def self.apply_status(pkmn, status)
    return false unless pkmn.respond_to?(:status=)
    real_status = status.respond_to?(:to_sym) ? status.to_sym : status
    return false if defined?(GameData::Status) && !GameData::Status.try_get(real_status)
    pkmn.status = real_status
    if real_status == :SLEEP && pkmn.respond_to?(:statusCount=)
      pkmn.statusCount = 2 + rand(3)
    end
    apply_status_to_active_battler(pkmn, real_status)
    true
  end

  def self.apply_status_to_active_battler(pkmn, status)
    return unless defined?($game_temp) && $game_temp
    battle = $game_temp.respond_to?(:battle) ? $game_temp.battle : nil
    return unless battle && battle.respond_to?(:battlers)
    battle.battlers.compact.each do |battler|
      next unless battler.respond_to?(:pokemon) && battler.pokemon.equal?(pkmn)
      if battler.respond_to?(:status=)
        battler.status = status
      end
      if status == :SLEEP && battler.respond_to?(:statusCount=)
        battler.statusCount = pkmn.respond_to?(:statusCount) ? pkmn.statusCount : 2 + rand(3)
      end
      if battler.respond_to?(:pbUpdate)
        battler.pbUpdate(false)
      end
    end
  rescue => e
    log("pokemon_lottery_status battle refresh skipped: #{e.message}")
  end

  def self.pokemon_lottery_status
    current_party = party
    raise "party is not ready" unless current_party
    targets = current_party.compact.select { |pkmn| can_receive_status?(pkmn) }
    if targets.empty?
      unless @lottery_no_targets_locked
        log("pokemon_lottery_status skipped: no valid targets")
        @lottery_no_targets_locked = true
      end
      return
    end
    @lottery_no_targets_locked = false
    amount = 1 + rand(3)
    chosen = targets.shuffle.first(amount)
    statuses = status_pool.shuffle
    applied = 0
    results = []
    chosen.each_with_index do |pkmn, index|
      status, code, label = statuses[index % statuses.length]
      if apply_status(pkmn, status)
        applied += 1
        name = pkmn.respond_to?(:name) ? pkmn.name.to_s : "Pokemon"
        results << "#{code}:#{name}"
      end
    end
    log("pokemon_lottery_status MIX #{applied}/#{amount} #{results.join(',')}")
  end

  def self.replace_all_party_with_random_pokedex_safe
    raise "party is not ready" unless defined?($player) && $player && $player.respond_to?(:party)
    party = $player.party
    raise "party is empty" if !party || party.empty?
    species = random_species_pool
    raise "species data is not ready" if species.empty?
    changed = 0
    party.each_with_index do |old_pkmn, index|
      next unless old_pkmn
      level = old_pkmn.respond_to?(:level) ? old_pkmn.level : 5
      level = [[level.to_i, 1].max, 100].min
      new_species = species[rand(species.length)]
      party[index] = create_pokemon(new_species, level)
      changed += 1
    end
    log("replaced full party with #{changed} random pokemon")
  end

  def self.random_species_pool
    if defined?(GameData::Species) && GameData::Species.respond_to?(:each)
      pool = []
      GameData::Species.each do |species_data|
        id = species_data.respond_to?(:id) ? species_data.id : nil
        next if id.nil?
        next if species_data.respond_to?(:egg?) && species_data.egg?
        next if species_data.respond_to?(:form) && species_data.form.to_i != 0
        pool << id
      end
      return pool
    end
    []
  rescue
    []
  end

  def self.create_pokemon(species, level)
    if defined?(Pokemon)
      return Pokemon.new(species, level)
    end
    raise "Pokemon class is not ready"
  end
end

LiveChaosAnil.start
