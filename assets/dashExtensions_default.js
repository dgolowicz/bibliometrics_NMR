window.dashExtensions = Object.assign({}, window.dashExtensions, {
    default: {
        function0: function(feature, context) {
            // If a style for the country exists in the hideout, use it.
            if (context.hideout && context.hideout.styles && context.hideout.styles[feature.properties.ISO_A2]) {
                return context.hideout.styles[feature.properties.ISO_A2];
            }
            // Otherwise, return a default style.
            return {
                color: 'black',
                weight: 1,
                fillOpacity: 0.1
            };
        }

    }
});