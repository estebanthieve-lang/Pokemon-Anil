module LiveChaosAnil
  ROOT = File.expand_path("../..", File.dirname(__FILE__))
  COMMAND_FILE = File.join(ROOT, "live_chaos_queue.txt")
  LOG_FILE = File.join(ROOT, "live_chaos_log.txt")

  @file_position = 0
  @queue = []
  @started = false

  def self.log(message)
    File.open(LOG_FILE, "a") { |file| file.puts("#{Time.now} #{message}") } rescue nil
  end

  def self.start
    return if @started
    @started = true
    log("postload starting")
    hook_scene_map
  end

  def self.hook_scene_map
    if defined?(Scene_Map)
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
    else
      log("Scene_Map not defined")
    end
  rescue => e
    log("Scene_Map hook failed: #{e.class}: #{e.message}")
  end

  def self.process_queue
    poll_command_file
    while @queue.length > 0
      execute(@queue.shift)
    end
  end

  def self.poll_command_file
    return unless File.exist?(COMMAND_FILE)
    File.open(COMMAND_FILE, "r") do |file|
      file.seek(@file_position, IO::SEEK_SET)
      file.each_line do |line|
        handle_line(line.strip)
      end
      @file_position = file.pos
    end
  rescue => e
    log("file bridge failed: #{e.class}: #{e.message}")
  end

  def self.handle_line(line)
    return if line.nil? || line.empty?
    parts = line.split(/\s+/)
    command = parts.shift.to_s
    case command
    when "add_item"
      item = parts.shift.to_s.upcase
      quantity = parts.shift.to_i
      quantity = 1 if quantity < 1
      quantity = 99 if quantity > 99
      @queue << { :type => :add_item, :item => item, :quantity => quantity }
      log("queued add_item #{item} #{quantity}")
    when "heal_party"
      @queue << { :type => :heal_party }
      log("queued heal_party")
    else
      log("unknown command #{line}")
    end
  end

  def self.execute(payload)
    case payload[:type]
    when :add_item
      add_item(payload[:item], payload[:quantity])
    when :heal_party
      heal_party
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
end

LiveChaosAnil.start
