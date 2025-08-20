"""
Monkey patch for fugashi to use GenericTagger instead of Tagger
This fixes the MeCab dictionary format issue with Coqui TTS
"""
import sys

try:
    import fugashi
    
    # Store the original Tagger class
    _original_tagger = fugashi.Tagger

    class NodeWrapper:
        """Wrapper to add missing attributes to Node objects for TTS compatibility"""
        def __init__(self, node):
            self._node = node
            
            # Handle the case where node might be a tuple directly
            if isinstance(node, tuple):
                # If we get a tuple directly, create a minimal node-like object
                features = node
                self.surface = '*'
                self.feature = node
                self.pos1 = features[0] if len(features) > 0 else '*'
                self.pos2 = features[1] if len(features) > 1 else '*'
                self.pos3 = features[2] if len(features) > 2 else '*'
                self.pos4 = features[3] if len(features) > 3 else '*'
                self.inflection = features[4] if len(features) > 4 else '*'
                self.conjugation = features[5] if len(features) > 5 else '*'
                self.base_form = features[6] if len(features) > 6 else '*'
                self.reading = features[7] if len(features) > 7 else '*'
                self.pronunciation = features[8] if len(features) > 8 else '*'
                # Set other common attributes
                self.char_type = 0
                self.is_unk = False
                self.length = 1
                self.rlength = 1
                self.posid = 0
                self.stat = 0
                self.white_space = False
                return
            
            # Copy all original attributes first
            for attr in dir(node):
                if not attr.startswith('_') and not callable(getattr(node, attr)):
                    try:
                        setattr(self, attr, getattr(node, attr))
                    except (AttributeError, TypeError):
                        # Skip attributes that can't be copied
                        pass
            
            # Add missing attributes by parsing the feature tuple
            if hasattr(node, 'feature') and isinstance(node.feature, tuple):
                features = node.feature
                self.pos1 = features[0] if len(features) > 0 else '*'
                self.pos2 = features[1] if len(features) > 1 else '*'
                self.pos3 = features[2] if len(features) > 2 else '*'
                self.pos4 = features[3] if len(features) > 3 else '*'
                self.inflection = features[4] if len(features) > 4 else '*'
                self.conjugation = features[5] if len(features) > 5 else '*'
                self.base_form = features[6] if len(features) > 6 else getattr(node, 'surface', '*')
                self.reading = features[7] if len(features) > 7 else getattr(node, 'surface', '*')
                self.pronunciation = features[8] if len(features) > 8 else getattr(node, 'surface', '*')
            else:
                # Default values when no feature tuple is available
                self.pos1 = '*'
                self.pos2 = '*'
                self.pos3 = '*'
                self.pos4 = '*'
                self.inflection = '*'
                self.conjugation = '*'
                self.base_form = getattr(node, 'surface', '*')
                self.reading = getattr(node, 'surface', '*')
                self.pronunciation = getattr(node, 'surface', '*')
        
        def __getattr__(self, name):
            """Forward any missing attributes to the original node"""
            if hasattr(self, '_node') and self._node is not None:
                try:
                    return getattr(self._node, name)
                except AttributeError:
                    pass
            # Return a safe default for missing attributes
            return '*'

    class PatchedTagger(fugashi.GenericTagger):
        """
        A patched version of fugashi.Tagger that uses GenericTagger internally
        and wraps Node objects for compatibility
        """
        def __init__(self, *args, **kwargs):
            # Initialize with GenericTagger instead of the original Tagger
            super().__init__(*args, **kwargs)
            
        def __call__(self, text):
            """Parse text and return wrapped nodes"""
            result = super().__call__(text)
            # Wrap each node to add missing attributes
            wrapped_result = [NodeWrapper(node) for node in result]
            return wrapped_result
            
        def parse(self, text):
            """Alternative parse method"""
            return self.__call__(text)

    def apply_fugashi_patch():
        """Apply the fugashi patch to fix MeCab dictionary issues"""
        fugashi.Tagger = PatchedTagger
        print("Applied fugashi patch: Using GenericTagger for Japanese text processing")

    def restore_fugashi():
        """Restore the original fugashi.Tagger"""
        fugashi.Tagger = _original_tagger
        print("Restored original fugashi.Tagger")
        
    # Auto-apply the patch when this module is imported
    apply_fugashi_patch()
    
except ImportError as e:
    print(f"Could not import fugashi: {e}")
    
    def apply_fugashi_patch():
        """Dummy function when fugashi is not available"""
        print("Fugashi not available, patch not applied")
        
    def restore_fugashi():
        """Dummy function when fugashi is not available"""
        print("Fugashi not available, nothing to restore")
