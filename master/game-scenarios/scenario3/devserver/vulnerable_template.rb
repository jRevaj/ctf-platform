# frozen_string_literal: true

module Gitlab
  module Template
    # Vulnerable template renderer for CTF challenge
    # This is a simplified version for demonstration purposes
    class VulnerableRenderer
      def initialize(template_content)
        @template_content = template_content
      end

      def render(params = {})
        # Vulnerable code - allows server-side template injection
        # In a real application, this would be more complex
        result = @template_content.dup
        
        # Replace variables in the template
        params.each do |key, value|
          result.gsub!("{{#{key}}}", value.to_s)
        end
        
        # Dangerous eval for template expressions (vulnerability)
        result.gsub!(/\{\{eval:(.*?)\}\}/) do
          begin
            eval($1) # Vulnerable to SSTI
          rescue => e
            "Error: #{e.message}"
          end
        end
        
        result
      end
    end
  end
end 