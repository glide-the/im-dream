-- [Input] Explicit inspect, or screenshot-relative click coordinates, for the existing iPhone Mirroring window.
-- [Output] Window bounds or one click in the verified mirror window; no keyboard text or credentials.
-- [Pos] Private desktop harness; execution requires the user's explicit alternative-automation instruction.
on run arguments
    tell application "System Events"
        set mirrorProcess to first application process whose bundle identifier is "com.apple.ScreenContinuity"
        tell mirrorProcess
            set frontmost to true
            set mirrorWindow to first window
            set windowPosition to position of mirrorWindow
            set windowSize to size of mirrorWindow
        end tell
        if (item 1 of arguments) is "inspect" then
            return {windowPosition, windowSize}
        end if
        if (item 1 of arguments) is not "click" then error "Unsupported mirror action"
        if (count arguments) is not 5 then error "Expected click x y screenshot-width screenshot-height"
        set localX to (item 2 of arguments) as real
        set localY to (item 3 of arguments) as real
        set imageWidth to (item 4 of arguments) as real
        set imageHeight to (item 5 of arguments) as real
        if localX < 0 or localY < 0 or localX > imageWidth or localY > imageHeight then error "Outside screenshot"
        set targetX to (item 1 of windowPosition) + localX * (item 1 of windowSize) / imageWidth
        set targetY to (item 2 of windowPosition) + localY * (item 2 of windowSize) / imageHeight
        click at {targetX, targetY}
    end tell
end run
