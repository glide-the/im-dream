#!/usr/bin/env ruby
# [Input] Explicit private output directory, installed xcodeproj and this test source.
# [Output] A generated UI-testing project without an application dependency.
# [Pos] Test-only preparation; production project, services and credentials remain unchanged.
require 'fileutils'
require 'pathname'
require 'xcodeproj'

abort 'Usage: prepare-ui-runner.rb ABSOLUTE_OUTPUT_DIRECTORY' unless ARGV.length == 1
root = Pathname.new(ARGV.fetch(0)).expand_path
abort 'Use a dedicated new output directory' if root.exist?
FileUtils.mkdir_p(root, mode: 0o700)
(root + '.ink-ios-ui-runner').write("ink-ios-ui-runner-v1\n")
project = Xcodeproj::Project.new((root + 'InkNativeUITests.xcodeproj').to_s)
target = project.new_target(:ui_test_bundle, 'InkNativeUITests', :ios, '18.0')
source = project.main_group.new_file(File.expand_path('DeckScrollUITests.swift', __dir__))
target.add_file_references([source])
target.build_configurations.each do |config|
  config.build_settings.merge!({
    'PRODUCT_BUNDLE_IDENTIFIER' => 'com.inkmemory.uiqualification',
    'GENERATE_INFOPLIST_FILE' => 'YES', 'SWIFT_VERSION' => '5.0',
    'CODE_SIGNING_ALLOWED' => 'NO', 'TARGETED_DEVICE_FAMILY' => '1,2',
    'SDKROOT' => 'iphonesimulator',
    'LD_RUNPATH_SEARCH_PATHS' => ['$(inherited)', '@executable_path/Frameworks', '@loader_path/Frameworks'],
  })
end
project.save
scheme = Xcodeproj::XCScheme.new
scheme.add_build_target(target)
scheme.add_test_target(target)
scheme.test_action.build_configuration = 'Debug'
scheme.save_as(project.path, 'InkNativeUITests', true)
puts project.path
